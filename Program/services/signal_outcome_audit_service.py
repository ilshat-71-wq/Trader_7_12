"""Offline, look-ahead-safe evaluation of timestamped Trader_7_12 signals.

This module is deliberately separate from live signal generation. It never
fetches data, changes model outputs, or executes trades. Callers must supply
real historical candles and an immutable signal record captured at signal time.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif value is not None:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except (TypeError, ValueError):
            return None
    else:
        return None
    # Naive timestamps are rejected: comparing naive local time to exchange
    # timestamps can silently introduce look-ahead or ordering errors.
    if dt.tzinfo is None:
        return None
    return dt


def normalize_signal(signal: dict[str, Any]) -> dict[str, Any]:
    """Validate and freeze the minimum data required to evaluate a signal."""
    ticker = str(signal.get("ticker") or signal.get("spot_ticker") or signal.get("futures_ticker") or "").strip().upper()
    direction = str(signal.get("direction") or signal.get("signal") or "").strip().upper()
    instrument_type = str(signal.get("instrument_type") or ("FUTURES" if signal.get("futures_ticker") else "SPOT")).strip().upper()
    timestamp = _timestamp(signal.get("signal_time") or signal.get("timestamp") or signal.get("generated_at"))
    entry = _number(signal.get("entry_price") if signal.get("entry_price") is not None else signal.get("price"))
    if not ticker:
        raise ValueError("signal ticker is required")
    if direction not in {"LONG", "SHORT"}:
        raise ValueError("signal direction must be LONG or SHORT")
    if instrument_type not in {"SPOT", "FUTURES"}:
        raise ValueError("instrument_type must be SPOT or FUTURES")
    if timestamp is None:
        raise ValueError("signal_time must be an ISO timestamp with timezone")
    if entry is None or entry <= 0:
        raise ValueError("entry_price must be a positive number")
    record = {
        "schema_version": SCHEMA_VERSION,
        "ticker": ticker,
        "instrument_type": instrument_type,
        "direction": direction,
        "signal_time": timestamp.isoformat(),
        "entry_price": entry,
    }
    # Preserve relevant source/model fields, but never overwrite canonical keys.
    for key in (
        "signal_id", "signal_model", "model_version", "probability",
        "signal_probability", "radar", "phase", "setup", "entry_trigger",
        "stop_price", "target_price", "snapshot_version", "data_status",
        "class_code", "futures_ticker", "spot_ticker",
    ):
        if key in signal and key not in record:
            record[key] = signal[key]
    return record


class SignalOutcomeJournal:
    """Append-only JSONL journal; one complete event per line."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload.setdefault("schema_version", SCHEMA_VERSION)
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid journal JSON on line {line_number}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"journal line {line_number} must contain an object")
                rows.append(value)
        return rows


def evaluate_signal(
    signal: dict[str, Any],
    candles: Iterable[dict[str, Any]],
    *,
    target_pct: float = 1.0,
    stop_pct: float | None = None,
    max_bars: int = 60,
    round_trip_cost_bps: float = 0.0,
) -> dict[str, Any]:
    """Evaluate future candles only, reporting ambiguous same-candle barriers.

    target_pct is the underlying price move in percent, not return on account
    equity. stop_pct is optional and is measured from entry. A signal-provided
    stop_price takes precedence over stop_pct. Candles require timezone-aware
    time/timestamp plus high/low/close. Bars at or before signal_time are ignored.
    """
    frozen = normalize_signal(signal)
    if target_pct <= 0:
        raise ValueError("target_pct must be positive")
    if max_bars < 1:
        raise ValueError("max_bars must be >= 1")
    if round_trip_cost_bps < 0:
        raise ValueError("round_trip_cost_bps cannot be negative")

    direction = frozen["direction"]
    entry = frozen["entry_price"]
    sign = 1.0 if direction == "LONG" else -1.0
    target_pct = float(target_pct)
    target = entry * (1.0 + sign * target_pct / 100.0)

    explicit_stop = _number(signal.get("stop_price"))
    if explicit_stop is not None and explicit_stop > 0:
        stop = explicit_stop
    elif stop_pct is not None and stop_pct > 0:
        stop = entry * (1.0 - sign * float(stop_pct) / 100.0)
    else:
        stop = None

    signal_time = _timestamp(frozen["signal_time"])
    future = []
    for candle in candles or []:
        candle_time = _timestamp(candle.get("time") or candle.get("timestamp") or candle.get("datetime"))
        high = _number(candle.get("high"))
        low = _number(candle.get("low"))
        close = _number(candle.get("close"))
        if candle_time is None or high is None or low is None or close is None:
            continue
        if high < low or low <= 0 or close <= 0:
            continue
        if candle_time <= signal_time:
            continue
        future.append((candle_time, high, low, close))
    future.sort(key=lambda item: item[0])
    future = future[:max_bars]

    max_favorable = 0.0
    max_adverse = 0.0
    target_time = None
    stop_time = None
    ambiguous_time = None
    last_close = entry
    bars_evaluated = 0

    for candle_time, high, low, close in future:
        bars_evaluated += 1
        last_close = close
        if direction == "LONG":
            favorable = (high / entry - 1.0) * 100.0
            adverse = (low / entry - 1.0) * 100.0
            hit_target = high >= target
            hit_stop = stop is not None and low <= stop
        else:
            favorable = (entry / low - 1.0) * 100.0
            adverse = (entry / high - 1.0) * 100.0
            hit_target = low <= target
            hit_stop = stop is not None and high >= stop
        max_favorable = max(max_favorable, favorable)
        max_adverse = min(max_adverse, adverse)

        if hit_target and hit_stop:
            ambiguous_time = candle_time.isoformat()
            break
        if hit_target:
            target_time = candle_time.isoformat()
            break
        if hit_stop:
            stop_time = candle_time.isoformat()
            break

    if ambiguous_time:
        outcome = "AMBIGUOUS_SAME_BAR"
        gross_return_pct = None
    elif target_time:
        outcome = "TARGET_FIRST"
        gross_return_pct = target_pct
    elif stop_time:
        outcome = "STOP_FIRST"
        gross_return_pct = ((stop / entry) - 1.0) * 100.0 * sign if stop else None
    elif bars_evaluated >= max_bars:
        outcome = "HORIZON_END"
        gross_return_pct = ((last_close / entry) - 1.0) * 100.0 * sign
    elif bars_evaluated:
        # A partial history is not a completed evaluation horizon.
        outcome = "PENDING_HORIZON"
        gross_return_pct = None
    else:
        outcome = "NO_FUTURE_DATA"
        gross_return_pct = None

    cost_pct = float(round_trip_cost_bps) / 100.0
    net_return_pct = None if gross_return_pct is None else gross_return_pct - cost_pct
    return {
        **frozen,
        "target_pct": target_pct,
        "target_price": round(target, 10),
        "stop_price_used": stop,
        "max_bars": max_bars,
        "bars_evaluated": bars_evaluated,
        "outcome": outcome,
        "target_time": target_time,
        "stop_time": stop_time,
        "ambiguous_time": ambiguous_time,
        "mfe_pct": round(max_favorable, 6),
        "mae_pct": round(max_adverse, 6),
        "gross_return_pct": None if gross_return_pct is None else round(gross_return_pct, 6),
        "round_trip_cost_bps": float(round_trip_cost_bps),
        "net_return_pct": None if net_return_pct is None else round(net_return_pct, 6),
        "outcome_status": (
            "EVALUATED" if outcome in {"TARGET_FIRST", "STOP_FIRST", "HORIZON_END", "AMBIGUOUS_SAME_BAR"}
            else "PENDING" if outcome == "PENDING_HORIZON"
            else "NO_DATA"
        ),
    }



def summarize_model_quality(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate confidence calibration against the observed target-within-horizon event.

    Only TARGET_FIRST, STOP_FIRST and HORIZON_END are resolved labels.
    Same-bar ambiguity and missing/unresolved data are excluded, never guessed.
    """
    records = list(rows or [])
    resolved = []
    for row in records:
        outcome = str(row.get("outcome") or "").upper()
        if outcome not in {"TARGET_FIRST", "STOP_FIRST", "HORIZON_END"}:
            continue
        probability = _number(
            row.get("signal_probability")
            if row.get("signal_probability") is not None
            else row.get("probability")
        )
        if probability is None or not 0.0 <= probability <= 100.0:
            continue
        resolved.append({
            **row,
            "_p": probability / 100.0,
            "_y": 1.0 if outcome == "TARGET_FIRST" else 0.0,
        })

    def metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            return {
                "resolved": 0, "target_first": 0, "target_rate_pct": None,
                "mean_predicted_probability_pct": None,
                "observed_target_rate_pct": None, "calibration_gap_pp": None,
                "brier_score": None,
            }
        predicted = sum(x["_p"] for x in items) / len(items)
        observed = sum(x["_y"] for x in items) / len(items)
        return {
            "resolved": len(items),
            "target_first": sum(int(x["_y"]) for x in items),
            "target_rate_pct": round(observed * 100.0, 3),
            "mean_predicted_probability_pct": round(predicted * 100.0, 3),
            "observed_target_rate_pct": round(observed * 100.0, 3),
            "calibration_gap_pp": round((predicted - observed) * 100.0, 3),
            "brier_score": round(sum((x["_p"] - x["_y"]) ** 2 for x in items) / len(items), 6),
        }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in resolved:
        key = ":".join((
            str(row.get("instrument_type") or "UNKNOWN").upper(),
            str(row.get("direction") or "UNKNOWN").upper(),
            str(row.get("phase") or "UNKNOWN").upper(),
        ))
        grouped.setdefault(key, []).append(row)

    bins = []
    for lower in range(0, 100, 10):
        upper = lower + 10
        members = [
            x for x in resolved
            if lower <= x["_p"] * 100.0 < upper
            or (upper == 100 and x["_p"] * 100.0 == 100)
        ]
        if members:
            bins.append({"probability_range": f"{lower}-{upper}%", **metrics(members)})

    return {
        "definition": "TARGET_FIRST within configured target/stop/horizon; resolved labels only",
        "records_seen": len(records),
        "resolved": len(resolved),
        "excluded": len(records) - len(resolved),
        "overall": metrics(resolved),
        "by_instrument_direction_phase": {
            key: metrics(items) for key, items in sorted(grouped.items())
        },
        "calibration_bins": bins,
    }


def summarize_outcomes(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate by instrument type/direction without mixing ambiguous records."""
    data = list(rows or [])
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in data:
        key = f"{str(row.get('instrument_type') or 'UNKNOWN').upper()}:{str(row.get('direction') or 'UNKNOWN').upper()}"
        groups.setdefault(key, []).append(row)

    def stats(items: list[dict[str, Any]]) -> dict[str, Any]:
        evaluated = [x for x in items if x.get("outcome") in {
            "TARGET_FIRST", "STOP_FIRST", "HORIZON_END", "AMBIGUOUS_SAME_BAR"
        }]
        target_first = sum(x.get("outcome") == "TARGET_FIRST" for x in evaluated)
        stop_first = sum(x.get("outcome") == "STOP_FIRST" for x in evaluated)
        ambiguous = sum(x.get("outcome") == "AMBIGUOUS_SAME_BAR" for x in evaluated)
        net = [_number(x.get("net_return_pct")) for x in evaluated]
        net = [x for x in net if x is not None]
        return {
            "signals": len(items),
            "evaluated": len(evaluated),
            "no_future_data": sum(x.get("outcome") == "NO_FUTURE_DATA" for x in items),
            "target_first": target_first,
            "stop_first": stop_first,
            "ambiguous": ambiguous,
            "target_first_pct": round(100.0 * target_first / len(evaluated), 2) if evaluated else None,
            "mean_net_return_pct": round(sum(net) / len(net), 6) if net else None,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "signals": len(data),
        "groups": {key: stats(items) for key, items in sorted(groups.items())},
        "overall": stats(data),
    }
