"""Trader_7_12 Pro — automated Morning Radar history and schedule."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo


class MorningRadarService:
    """Persist and compare the scheduled morning market snapshots.

    The service is deliberately read-only. It never changes the production
    scanner's ranking or places orders. It records the existing real-data
    snapshot and derives transparent morning deltas from it.
    """

    TIMEZONE = ZoneInfo("Europe/Moscow")
    SLOTS = (time(7, 0), time(7, 15), time(7, 30), time(8, 0),
             time(9, 0), time(9, 45), time(9, 50))
    VERSION = "1.0.0"
    MAX_DAYS = 14
    MAX_COUNTERTREND = 10

    def __init__(self, data_dir: str | None = None):
        root = data_dir or os.getenv(
            "MORNING_RADAR_DATA_DIR",
            str(Path(__file__).resolve().parent / "data" / "morning_radar"),
        )
        self.data_dir = Path(root)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def today_key(cls, value: datetime | None = None) -> str:
        value = value or datetime.now(cls.TIMEZONE)
        return value.astimezone(cls.TIMEZONE).date().isoformat()

    def _path(self, trading_date: str) -> Path:
        return self.data_dir / f"{trading_date}.json"

    def load(self, trading_date: str | None = None) -> dict:
        trading_date = trading_date or self.today_key()
        path = self._path(trading_date)
        if not path.exists():
            return {
                "version": self.VERSION,
                "trading_date": trading_date,
                "slots": [x.strftime("%H:%M") for x in self.SLOTS],
                "snapshots": [],
                "status": "EMPTY",
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid payload")
            return payload
        except (OSError, ValueError, json.JSONDecodeError):
            return {
                "version": self.VERSION,
                "trading_date": trading_date,
                "slots": [x.strftime("%H:%M") for x in self.SLOTS],
                "snapshots": [],
                "status": "CORRUPT",
            }

    def _save(self, trading_date: str, payload: dict) -> None:
        path = self._path(trading_date)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{trading_date}.",
            suffix=".tmp",
            dir=str(self.data_dir),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_name, path)
        finally:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _compact_row(cls, row: dict) -> dict:
        keys = (
            "spot_ticker", "change_percent", "relative_strength",
            "money_per_minute", "recent_money_per_minute", "recent_money",
            "session_money", "money_acceleration", "attention_score",
            "directional_score", "signal", "signal_probability",
            "signal_probability_delta", "daily_relative_mean_pp",
            "daily_qualified", "liquidity_gate", "qualification_status",
            "selection_role", "watch_reason",
        )
        return {key: row.get(key) for key in keys if key in row}

    @classmethod
    def _compact_countertrend(cls, row: dict) -> dict:
        keys = (
            "spot_ticker", "change_percent", "relative_strength",
            "money_per_minute", "recent_money_per_minute", "recent_money",
            "money_acceleration", "attention_score", "directional_score",
            "signal", "signal_probability", "daily_relative_mean_pp",
            "daily_qualified", "liquidity_gate",
        )
        return {key: row.get(key) for key in keys if key in row}

    @classmethod
    def _snapshot_record(cls, snapshot: dict, slot: str | None) -> dict:
        diagnostics = snapshot.get("radar_diagnostics") or {}
        rows = snapshot.get("radar") or []
        generated = snapshot.get("generated_at") or datetime.now(cls.TIMEZONE).isoformat()
        return {
            "slot": slot,
            "generated_at": generated,
            "benchmark": diagnostics.get("benchmark"),
            "benchmark_change_percent": diagnostics.get("benchmark_change_percent"),
            "market_regime": diagnostics.get("market_regime"),
            "coverage_percent": diagnostics.get("coverage_percent"),
            "analyzed": diagnostics.get("analyzed"),
            "strict_selected": diagnostics.get("strict_selected"),
            "watch_selected": diagnostics.get("watch_selected"),
            "countertrend_watch": [
                cls._compact_countertrend(x)
                for x in (diagnostics.get("countertrend_watch") or [])[: cls.MAX_COUNTERTREND]
            ],
            "radar": [cls._compact_row(x) for x in rows],
            "futures_oi": snapshot.get("futures_oi") or [],
            "futures_diagnostics": snapshot.get("futures_diagnostics") or {},
            "timing": snapshot.get("timing") or {},
        }

    @classmethod
    def _row_map(cls, record: dict) -> dict[str, dict]:
        return {
            str(row.get("spot_ticker") or "").upper(): row
            for row in record.get("radar") or []
            if row.get("spot_ticker")
        }

    @classmethod
    def _interest_delta(cls, current: dict, previous: dict | None) -> dict:
        if previous is None:
            return {
                "state": "NEW",
                "pace_delta_pct": None,
                "recent_pace_delta_pct": None,
                "acceleration_delta_pp": None,
                "rs_delta_pp": None,
                "probability_delta_pp": None,
            }

        def pct_delta(now, before):
            before = cls._float(before)
            now = cls._float(now)
            if before <= 0:
                return None
            return round((now / before - 1.0) * 100.0, 1)

        pace = pct_delta(current.get("money_per_minute"), previous.get("money_per_minute"))
        recent = pct_delta(current.get("recent_money_per_minute"), previous.get("recent_money_per_minute"))
        accel = round(
            cls._float(current.get("money_acceleration"))
            - cls._float(previous.get("money_acceleration")), 1
        )
        rs = round(
            cls._float(current.get("relative_strength"))
            - cls._float(previous.get("relative_strength")), 2
        )
        prob = round(
            cls._float(current.get("signal_probability"))
            - cls._float(previous.get("signal_probability")), 1
        )

        rising = sum([
            1 if (pace is not None and pace > 8.0) else 0,
            1 if (recent is not None and recent > 8.0) else 0,
            1 if accel > 5.0 else 0,
            1 if rs > 0.05 else 0,
        ])
        falling = sum([
            1 if (pace is not None and pace < -8.0) else 0,
            1 if (recent is not None and recent < -8.0) else 0,
            1 if accel < -5.0 else 0,
            1 if rs < -0.05 else 0,
        ])
        state = "RISING" if rising >= 2 and rising > falling else (
            "FALLING" if falling >= 2 and falling > rising else "STABLE"
        )
        return {
            "state": state,
            "pace_delta_pct": pace,
            "recent_pace_delta_pct": recent,
            "acceleration_delta_pp": accel,
            "rs_delta_pp": rs,
            "probability_delta_pp": prob,
        }

    @classmethod
    def _decorate(cls, record: dict, previous: dict | None) -> dict:
        previous_map = cls._row_map(previous or {})
        rows = []
        for row in record.get("radar") or []:
            ticker = str(row.get("spot_ticker") or "").upper()
            item = dict(row)
            item["interest"] = cls._interest_delta(
                row, previous_map.get(ticker)
            )
            rows.append(item)

        counter = []
        for row in record.get("countertrend_watch") or []:
            ticker = str(row.get("spot_ticker") or "").upper()
            item = dict(row)
            item["interest"] = cls._interest_delta(
                row, previous_map.get(ticker)
            )
            counter.append(item)

        record = dict(record)
        record["radar"] = rows
        record["countertrend_watch"] = counter
        return record

    def record(self, snapshot: dict, slot: str | None = None) -> dict:
        generated = snapshot.get("generated_at")
        try:
            when = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
            when = when.astimezone(self.TIMEZONE)
        except (TypeError, ValueError):
            when = datetime.now(self.TIMEZONE)
        trading_date = when.date().isoformat()
        payload = self.load(trading_date)
        previous = payload.get("snapshots", [])[-1] if payload.get("snapshots") else None
        record = self._decorate(self._snapshot_record(snapshot, slot), previous)

        snapshots = list(payload.get("snapshots") or [])
        if slot:
            snapshots = [x for x in snapshots if x.get("slot") != slot]
        snapshots.append(record)
        snapshots.sort(key=lambda x: str(x.get("generated_at") or ""))
        payload.update({
            "version": self.VERSION,
            "trading_date": trading_date,
            "slots": [x.strftime("%H:%M") for x in self.SLOTS],
            "snapshots": snapshots,
            "status": "READY",
            "last_slot": record.get("slot"),
            "last_generated_at": record.get("generated_at"),
        })
        self._save(trading_date, payload)
        self._prune()
        return payload

    def _prune(self):
        files = sorted(self.data_dir.glob("*.json"), reverse=True)
        for path in files[self.MAX_DAYS:]:
            try:
                path.unlink()
            except OSError:
                pass

    @classmethod
    def slot_for(cls, value: datetime | None = None) -> str | None:
        value = (value or datetime.now(cls.TIMEZONE)).astimezone(cls.TIMEZONE)
        if value.second > 20:
            return None
        for slot in cls.SLOTS:
            if value.hour == slot.hour and value.minute == slot.minute:
                return slot.strftime("%H:%M")
        return None

    @classmethod
    def next_slot(cls, value: datetime | None = None) -> datetime | None:
        value = (value or datetime.now(cls.TIMEZONE)).astimezone(cls.TIMEZONE)
        today = value.date()
        for slot in cls.SLOTS:
            candidate = datetime.combine(today, slot, tzinfo=cls.TIMEZONE)
            if candidate > value:
                return candidate
        return datetime.combine(today + timedelta(days=1), cls.SLOTS[0], tzinfo=cls.TIMEZONE)

    def summary(self, trading_date: str | None = None) -> dict:
        payload = self.load(trading_date)
        snapshots = payload.get("snapshots") or []
        latest = snapshots[-1] if snapshots else None
        first = snapshots[0] if snapshots else None
        latest_rows = latest.get("radar") if latest else []
        rising = sum(1 for row in latest_rows if (row.get("interest") or {}).get("state") == "RISING")
        falling = sum(1 for row in latest_rows if (row.get("interest") or {}).get("state") == "FALLING")
        short_watch = latest.get("countertrend_watch") if latest else []
        return {
            "version": self.VERSION,
            "trading_date": payload.get("trading_date"),
            "status": payload.get("status", "EMPTY"),
            "slots": payload.get("slots", []),
            "completed_slots": [x.get("slot") for x in snapshots if x.get("slot")],
            "snapshot_count": len(snapshots),
            "first_slot": first.get("slot") if first else None,
            "last_slot": latest.get("slot") if latest else None,
            "market_regime": latest.get("market_regime") if latest else None,
            "benchmark_change_percent": latest.get("benchmark_change_percent") if latest else None,
            "benchmark": latest.get("benchmark") if latest else None,
            "interest_rising": rising,
            "interest_falling": falling,
            "short_watch_count": len(short_watch or []),
            "short_watch": short_watch or [],
            "latest": latest,
        }
