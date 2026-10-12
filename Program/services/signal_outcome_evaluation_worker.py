"""Bounded, append-only outcome evaluation using real closed BCS candles."""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from services.history_candle_service import HistoryCandleService
from services.signal_outcome_audit_service import SignalOutcomeJournal, evaluate_signal


class SignalOutcomeEvaluationWorker:
    """Evaluate a small batch of pending journal observations per invocation.

    The loader is injectable for tests. Production uses HistoryCandleService,
    which reads real BCS candles. No result is written until a barrier is hit
    or the full evaluation horizon has elapsed.
    """

    def __init__(
        self,
        journal: SignalOutcomeJournal,
        *,
        candle_loader: Callable[..., list[dict[str, Any]]] | None = None,
        max_signals_per_run: int = 2,
        timeframe_minutes: int = 5,
        max_bars: int = 60,
        target_pct: float = 1.0,
        stop_pct: float | None = None,
        round_trip_cost_bps: float = 10.0,
    ):
        self.journal = journal
        self.candle_loader = candle_loader
        self.max_signals_per_run = max(1, int(max_signals_per_run))
        self.timeframe_minutes = max(1, int(timeframe_minutes))
        self.max_bars = max(1, int(max_bars))
        self.target_pct = float(target_pct)
        self.stop_pct = stop_pct
        self.round_trip_cost_bps = float(round_trip_cost_bps)
        self._lock = threading.Lock()
        self._history_service = None

    def _load_candles(self, signal: dict[str, Any], start: datetime, end: datetime):
        if self.candle_loader is not None:
            return self.candle_loader(
                signal=signal,
                start_time=start.isoformat(),
                end_time=end.isoformat(),
                timeframe_minutes=self.timeframe_minutes,
            ) or []
        if self._history_service is None:
            self._history_service = HistoryCandleService()
        class_code = str(signal.get("class_code") or "").strip()
        ticker = str(signal.get("ticker") or "").strip().upper()
        if not class_code or not ticker:
            return []
        return self._history_service.load(
            ticker,
            class_code,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            timeframe_minutes=self.timeframe_minutes,
        ) or []

    def run_once(self, *, now: datetime | None = None) -> dict[str, int]:
        if not self._lock.acquire(blocking=False):
            return {"busy": 1, "checked": 0, "evaluated": 0, "no_data": 0}
        checked = evaluated = no_data = 0
        try:
            rows = self.journal.read_all()
            outcome_ids = {
                str(row.get("signal_id"))
                for row in rows
                if row.get("event") == "outcome" and row.get("signal_id")
            }
            source_by_id = {
                str(row.get("signal_id")): row
                for row in rows
                if row.get("event") == "signal_observation" and row.get("signal_id")
            }

            def episode_key(row):
                stamp = str(row.get("signal_time") or "")
                day = stamp[:10]
                return ":".join((
                    str(row.get("radar") or "UNKNOWN").upper(),
                    day,
                    str(row.get("instrument_type") or "UNKNOWN").upper(),
                    str(row.get("ticker") or "").upper(),
                    str(row.get("direction") or row.get("signal") or "").upper(),
                ))

            # Periodic Cloud snapshots are correlated observations, not separate
            # trades. Evaluate only the earliest observation per same-day episode.
            resolved_episodes = {
                episode_key(source_by_id[signal_id])
                for signal_id in outcome_ids if signal_id in source_by_id
            }
            observations = {}
            for row in rows:
                if row.get("event") != "signal_observation" or not row.get("signal_id"):
                    continue
                signal_id = str(row["signal_id"])
                key = episode_key(row)
                if signal_id in outcome_ids or key in resolved_episodes:
                    continue
                current_row = observations.get(key)
                if current_row is None or str(row.get("signal_time") or "") < str(current_row.get("signal_time") or ""):
                    observations[key] = row

            current = now or datetime.now(timezone.utc)
            if current.tzinfo is None:
                raise ValueError("now must be timezone-aware")
            current = current.astimezone(timezone.utc)
            # BCS M5 candle timestamps mark bar start. Exclude the current
            # unfinished bar by ending history at the last completed 5-minute boundary.
            interval = timedelta(minutes=self.timeframe_minutes)
            cutoff = current.replace(second=0, microsecond=0)
            cutoff -= timedelta(minutes=cutoff.minute % self.timeframe_minutes)
            cutoff -= interval
            for episode, observation in sorted(
                observations.items(),
                key=lambda pair: str(pair[1].get("signal_time") or ""),
            )[: self.max_signals_per_run]:
                signal_id = str(observation["signal_id"])
                checked += 1
                signal_time_text = observation.get("signal_time")
                try:
                    signal_time = datetime.fromisoformat(
                        str(signal_time_text).replace("Z", "+00:00")
                    )
                    if signal_time.tzinfo is None:
                        continue
                    signal_time = signal_time.astimezone(timezone.utc)
                except (TypeError, ValueError):
                    continue
                if signal_time >= cutoff:
                    no_data += 1
                    continue
                candles = self._load_candles(observation, signal_time, cutoff)
                closed = []
                for candle in candles:
                    try:
                        stamp = datetime.fromisoformat(
                            str(candle.get("time") or candle.get("timestamp") or "").replace("Z", "+00:00")
                        )
                        if stamp.tzinfo is None:
                            continue
                        if stamp.astimezone(timezone.utc) + interval <= current.astimezone(timezone.utc):
                            closed.append(candle)
                    except (TypeError, ValueError):
                        continue
                try:
                    result = evaluate_signal(
                        observation,
                        closed,
                        target_pct=self.target_pct,
                        stop_pct=self.stop_pct,
                        max_bars=self.max_bars,
                        round_trip_cost_bps=self.round_trip_cost_bps,
                    )
                except (TypeError, ValueError):
                    no_data += 1
                    continue
                if result["outcome"] in {"NO_FUTURE_DATA", "PENDING_HORIZON"}:
                    no_data += 1
                    continue
                outcome_time = (
                    result.get("target_time")
                    or result.get("stop_time")
                    or result.get("ambiguous_time")
                )
                if not outcome_time and closed:
                    outcome_time = str(closed[-1].get("time") or closed[-1].get("timestamp"))
                event = {
                    "event": "outcome",
                    "signal_id": signal_id,
                    "evaluated_at": current.isoformat(),
                    "outcome_time": outcome_time,
                    "time_to_outcome_minutes": None,
                    "data_source": "BCS_REAL_CLOSED_CANDLES",
                    "timeframe_minutes": self.timeframe_minutes,
                    **result,
                }
                if outcome_time:
                    try:
                        outcome_dt = datetime.fromisoformat(str(outcome_time).replace("Z", "+00:00"))
                        if outcome_dt.tzinfo is not None:
                            event["time_to_outcome_minutes"] = round(
                                (outcome_dt.astimezone(timezone.utc) - signal_time).total_seconds() / 60.0, 2
                            )
                    except (TypeError, ValueError):
                        pass
                self.journal.append(event)
                outcomes.add(signal_id)
                evaluated += 1
            return {"busy": 0, "checked": checked, "evaluated": evaluated, "no_data": no_data}
        finally:
            self._lock.release()
