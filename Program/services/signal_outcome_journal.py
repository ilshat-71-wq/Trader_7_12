"""Persistent, real-candle outcome journal for FINAL RADAR candidates.

Research/measurement only: no order execution and no claim that model probability
equals win probability. Net returns are reported only with an explicit round-trip
cost assumption.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
HORIZONS_MINUTES = (5, 15, 30, 60)


class SignalOutcomeJournal:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else (
            Path.home() / "Library" / "Application Support" / "Trader_7_12"
            / "SignalOutcomeJournal.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @staticmethod
    def _number(value):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if isfinite(number) else None

    @staticmethod
    def _datetime(value):
        if isinstance(value, datetime):
            result = value
        else:
            try:
                result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return None
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.db_path), timeout=10)
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _initialize(self):
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS signal_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_key TEXT NOT NULL UNIQUE,
                    ticker TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    entry_price REAL,
                    class_code TEXT,
                    probability REAL,
                    phase TEXT,
                    atr_percent REAL,
                    atr_used_percent REAL,
                    session_money REAL,
                    money_per_minute REAL,
                    realtime_json TEXT NOT NULL DEFAULT '{}',
                    outcomes_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL,
                    data_reason TEXT
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_signal_outcomes_status ON signal_outcomes(status)")

    def record_candidates(self, candidates, now=None):
        """Persist FINAL rows once per MSK day/ticker/type/direction."""
        now = self._datetime(now or datetime.now(MOSCOW_TZ))
        if now is None:
            raise ValueError("now must be a valid datetime")
        local_now = now.astimezone(MOSCOW_TZ)
        inserted = 0
        with self._connect() as db:
            for item in candidates or []:
                if not isinstance(item, dict):
                    continue
                ticker = str(
                    item.get("final_ticker") or item.get("spot_ticker")
                    or item.get("futures_ticker") or ""
                ).strip().upper()
                direction = str(item.get("signal") or "").strip().upper()
                instrument_type = str(
                    item.get("final_instrument_type") or item.get("instrument_type") or ""
                ).strip().upper()
                if not ticker or direction not in {"LONG", "SHORT"}:
                    continue
                if instrument_type not in {"SPOT", "FUTURES"}:
                    instrument_type = "FUTURES" if item.get("futures_ticker") else "SPOT"
                price = next((
                    self._number(item.get(key)) for key in ("price", "last_price", "close")
                    if self._number(item.get(key)) is not None
                ), None)
                class_code = str(
                    item.get("spot_class_code") or item.get("futures_class_code")
                    or item.get("class_code") or ""
                ).strip().upper() or None
                reason = None
                if price is None or price <= 0:
                    reason = "ENTRY_PRICE_MISSING_OR_INVALID"
                elif not class_code:
                    reason = "BCS_CLASS_CODE_MISSING"
                signal_key = "|".join((
                    local_now.date().isoformat(), instrument_type, ticker, direction
                ))
                rt = {
                    key: item.get(key) for key in (
                        "book_score", "tape_score", "flow_score",
                        "final_realtime", "final_confirmations",
                    ) if item.get(key) is not None
                }
                cursor = db.execute("""
                    INSERT INTO signal_outcomes (
                        signal_key, ticker, instrument_type, direction, entry_time,
                        entry_price, class_code, probability, phase, atr_percent,
                        atr_used_percent, session_money, money_per_minute,
                        realtime_json, status, data_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(signal_key) DO UPDATE SET
                        entry_time=excluded.entry_time,
                        entry_price=excluded.entry_price,
                        class_code=excluded.class_code,
                        probability=excluded.probability,
                        phase=excluded.phase,
                        atr_percent=excluded.atr_percent,
                        atr_used_percent=excluded.atr_used_percent,
                        session_money=excluded.session_money,
                        money_per_minute=excluded.money_per_minute,
                        realtime_json=excluded.realtime_json,
                        status=excluded.status,
                        data_reason=excluded.data_reason
                    WHERE signal_outcomes.status='INCOMPLETE_DATA'
                      AND excluded.status='PENDING'
                """, (
                    signal_key, ticker, instrument_type, direction,
                    local_now.isoformat(timespec="seconds"), price, class_code,
                    self._number(item.get("signal_probability")),
                    str(item.get("move_phase") or item.get("phase") or "") or None,
                    self._number(item.get("atr_percent")),
                    self._number(item.get("atr_used_percent")),
                    self._number(item.get("session_money", item.get("turnover_rub"))),
                    self._number(item.get("money_per_minute")),
                    json.dumps(rt, ensure_ascii=False, allow_nan=False),
                    "PENDING" if reason is None else "INCOMPLETE_DATA", reason,
                ))
                inserted += cursor.rowcount
        return inserted

    def evaluate_pending(self, candle_loader, now=None, costs_bps=None):
        """Evaluate forward closed M5 candles supplied by a real-data provider.

        candle_loader(ticker, class_code, start_utc, end_utc) must return BCS
        candles. If costs_bps is omitted, net return stays null rather than
        silently assuming zero fees or slippage.
        """
        now = self._datetime(now or datetime.now(timezone.utc))
        if now is None:
            raise ValueError("now must be a valid datetime")
        now = now.astimezone(timezone.utc)
        cost = self._number(costs_bps)
        if cost is not None and cost < 0:
            raise ValueError("costs_bps cannot be negative")
        # If the fee assumption is added after earlier horizons completed,
        # update saved gross outcomes without needing to refetch historical candles.
        if cost is not None:
            with self._connect() as db:
                saved = db.execute(
                    "SELECT id, outcomes_json FROM signal_outcomes WHERE status IN ('PARTIAL', 'COMPLETE')"
                ).fetchall()
                for saved_id, saved_text in saved:
                    try:
                        saved_outcomes = json.loads(saved_text or "{}")
                    except (TypeError, ValueError):
                        continue
                    changed = False
                    for saved_result in saved_outcomes.values():
                        gross = self._number(saved_result.get("gross_close_return_pct"))
                        if gross is not None and saved_result.get("net_close_return_pct") is None:
                            saved_result["net_close_return_pct"] = round(gross - cost / 100.0, 5)
                            saved_result["cost_assumption_bps_round_trip"] = cost
                            changed = True
                    if changed:
                        db.execute(
                            "UPDATE signal_outcomes SET outcomes_json=? WHERE id=?",
                            (json.dumps(saved_outcomes, ensure_ascii=False, allow_nan=False), saved_id),
                        )
        with self._connect() as db:
            rows = db.execute("""
                SELECT id, ticker, direction, entry_time, entry_price, class_code, outcomes_json
                FROM signal_outcomes
                WHERE status IN ('PENDING', 'PARTIAL')
                  AND entry_price IS NOT NULL AND class_code IS NOT NULL
            """).fetchall()
        updated = 0
        for row in rows:
            row_id, ticker, direction, entry_text, entry_price, class_code, outcome_text = row
            entry_time = self._datetime(entry_text)
            if entry_time is None:
                continue
            entry_time = entry_time.astimezone(timezone.utc)
            try:
                candles = candle_loader(ticker, class_code, entry_time, now) or []
            except Exception:
                continue
            normalized = []
            for candle in candles:
                if not isinstance(candle, dict):
                    continue
                stamp = self._datetime(candle.get("time"))
                high, low, close = (
                    self._number(candle.get("high")),
                    self._number(candle.get("low")),
                    self._number(candle.get("close")),
                )
                if stamp is None or high is None or low is None or close is None:
                    continue
                stamp = stamp.astimezone(timezone.utc)
                if stamp < entry_time or min(high, low, close) <= 0 or high < low:
                    continue
                normalized.append((stamp, high, low, close))
            normalized.sort(key=lambda x: x[0])
            try:
                outcomes = json.loads(outcome_text or "{}")
            except (TypeError, ValueError):
                outcomes = {}
            for minutes in HORIZONS_MINUTES:
                key = str(minutes)
                cutoff = entry_time + timedelta(minutes=minutes)
                if key in outcomes:
                    # If actual costs are configured after gross outcomes were
                    # measured, derive net return from the saved gross result.
                    if cost is not None and outcomes[key].get("net_close_return_pct") is None:
                        gross_saved = self._number(outcomes[key].get("gross_close_return_pct"))
                        if gross_saved is not None:
                            outcomes[key]["net_close_return_pct"] = round(gross_saved - cost / 100.0, 5)
                            outcomes[key]["cost_assumption_bps_round_trip"] = cost
                    continue
                if now < cutoff:
                    continue
                eligible = [
                    c for c in normalized
                    if c[0] >= entry_time and c[0] + timedelta(minutes=5) <= cutoff
                ]
                if not eligible:
                    continue
                # A horizon needs a real closed candle at its end; an old
                # first candle must not be reused as a fake 15/30/60m result.
                if eligible[-1][0] + timedelta(minutes=5) < cutoff:
                    continue
                signed = 1.0 if direction == "LONG" else -1.0
                gross_close = ((eligible[-1][3] / entry_price) - 1.0) * 100.0 * signed
                if direction == "LONG":
                    mfe = max((c[1] / entry_price - 1.0) * 100.0 for c in eligible)
                    mae = max((1.0 - c[2] / entry_price) * 100.0 for c in eligible)
                else:
                    mfe = max((1.0 - c[2] / entry_price) * 100.0 for c in eligible)
                    mae = max((c[1] / entry_price - 1.0) * 100.0 for c in eligible)
                outcomes[key] = {
                    "horizon_minutes": minutes,
                    "closed_candles": len(eligible),
                    "gross_close_return_pct": round(gross_close, 5),
                    "mfe_pct": round(max(0.0, mfe), 5),
                    "mae_pct": round(max(0.0, mae), 5),
                    "net_close_return_pct": (
                        round(gross_close - cost / 100.0, 5) if cost is not None else None
                    ),
                    "cost_assumption_bps_round_trip": cost,
                    "source": "BCS_CLOSED_M5",
                }
            status = "COMPLETE" if all(str(h) in outcomes for h in HORIZONS_MINUTES) else "PARTIAL"
            with self._connect() as db:
                db.execute(
                    "UPDATE signal_outcomes SET outcomes_json=?, status=?, data_reason=NULL WHERE id=?",
                    (json.dumps(outcomes, ensure_ascii=False, allow_nan=False), status, row_id),
                )
            updated += 1
        return updated

    def summary(self):
        with self._connect() as db:
            rows = db.execute(
                "SELECT status, COUNT(*) FROM signal_outcomes GROUP BY status"
            ).fetchall()
        return {status: count for status, count in rows}

    @staticmethod
    def _return_stats(values):
        clean = [value for value in values if value is not None and isfinite(value)]
        if not clean:
            return {
                "sample_size": 0,
                "mean_pct": None,
                "median_pct": None,
                "win_rate_pct": None,
            }
        ordered = sorted(clean)
        middle = len(ordered) // 2
        median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0
        return {
            "sample_size": len(clean),
            "mean_pct": round(sum(clean) / len(clean), 5),
            "median_pct": round(median, 5),
            "win_rate_pct": round(sum(1 for value in clean if value > 0) / len(clean) * 100.0, 2),
        }

    def performance_summary(self):
        """Aggregate only measured forward-candle outcomes; never infer missing net returns."""
        records = self.records()
        result = {
            "record_count": len(records),
            "status_counts": self.summary(),
            "horizons": {},
            "by_phase_direction": {},
            "warning": (
                "Observational signal outcomes, not executed trades. Signals may be correlated; "
                "net statistics include only records with an explicit round-trip cost assumption."
            ),
        }
        for minutes in HORIZONS_MINUTES:
            key = str(minutes)
            available = [
                row for row in records
                if key in (row.get("outcomes") or {})
                and (row["outcomes"][key].get("source") == "BCS_CLOSED_M5")
            ]
            gross = [
                self._number(row["outcomes"][key].get("gross_close_return_pct"))
                for row in available
            ]
            net = [
                self._number(row["outcomes"][key].get("net_close_return_pct"))
                for row in available
            ]
            result["horizons"][key] = {
                "gross": self._return_stats(gross),
                "net": self._return_stats(net),
                "net_cost_assumption_count": sum(value is not None for value in net),
            }
            groups = {}
            for row in available:
                group_key = "|".join((
                    str(row.get("phase") or "UNKNOWN").upper(),
                    str(row.get("direction") or "UNKNOWN").upper(),
                ))
                groups.setdefault(group_key, {"gross": [], "net": []})
                outcome = row["outcomes"][key]
                groups[group_key]["gross"].append(self._number(outcome.get("gross_close_return_pct")))
                groups[group_key]["net"].append(self._number(outcome.get("net_close_return_pct")))
            result["by_phase_direction"][key] = {
                group_key: {
                    "gross": self._return_stats(values["gross"]),
                    "net": self._return_stats(values["net"]),
                }
                for group_key, values in sorted(groups.items())
            }
        return result

    def records(self):
        with self._connect() as db:
            rows = db.execute("""
                SELECT ticker, instrument_type, direction, entry_time, entry_price,
                       probability, phase, status, data_reason, outcomes_json
                FROM signal_outcomes ORDER BY entry_time DESC
            """).fetchall()
        return [
            {
                "ticker": r[0], "instrument_type": r[1], "direction": r[2],
                "entry_time": r[3], "entry_price": r[4], "probability": r[5],
                "phase": r[6], "status": r[7], "data_reason": r[8],
                "outcomes": json.loads(r[9] or "{}"),
            } for r in rows
        ]
