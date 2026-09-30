"""Real-data M1 entry confirmation for the SPOT Radar pipeline.

M1 is used only after D1 direction, H1 level context and an M5 setup exist.
No synthetic prices or volume are created.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from statistics import median
from zoneinfo import ZoneInfo


class SpotM1EntryService:
    TIMEFRAME_MINUTES = 1
    LOOKBACK_MINUTES = 30
    BASELINE_CANDLES = 10
    MIN_VOLUME_RATIO = 1.20
    MIN_CANDLES = 5
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    SESSION_WINDOWS = {
        "MORNING": (time(7, 0), time(9, 0)),
        "MAIN": (time(9, 0), time(19, 0)),
        "EVENING": (time(19, 0), time(23, 50)),
    }

    def __init__(self, history_service, session_service):
        self.history_service = history_service
        self.session_service = session_service

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def empty(cls, reason="NO_DATA"):
        return {
            "m1_entry_state": "UNAVAILABLE",
            "m1_volume_state": "UNAVAILABLE",
            "m1_volume_ratio": 0.0,
            "m1_entry_triggered": False,
            "m1_candle_count": 0,
            "m1_last_price": 0.0,
            "m1_last_money_volume": 0.0,
            "m1_reason": reason,
        }

    def _window(self, session, trading_date):
        start, end = self.SESSION_WINDOWS.get(str(session or "").upper(), (None, None))
        if start is None or trading_date is None:
            return None, None
        return (
            datetime.combine(trading_date, start, tzinfo=self.MOSCOW_TZ),
            datetime.combine(trading_date, end, tzinfo=self.MOSCOW_TZ),
        )

    def _load(self, ticker, class_code, session, trading_date, now=None):
        start, end = self._window(session, trading_date)
        if start is None:
            return []
        if now is not None:
            now_moscow = now.astimezone(self.MOSCOW_TZ)
            end = min(end, now_moscow)
        if end <= start:
            return []
        try:
            candles = self.history_service.load(
                ticker,
                class_code,
                start_time=start.astimezone(timezone.utc),
                end_time=end.astimezone(timezone.utc),
                timeframe_minutes=self.TIMEFRAME_MINUTES,
            )
        except Exception:
            return []
        rows = []
        for candle in candles or []:
            if not isinstance(candle, dict):
                continue
            try:
                dt = self.history_service.to_moscow(candle.get("time"))
            except Exception:
                dt = None
            close = self._f(candle.get("close"))
            volume = max(0.0, self._f(candle.get("money_volume", candle.get("volume"))))
            if dt is None or close <= 0 or volume <= 0:
                continue
            rows.append({**candle, "_dt": dt, "_volume": volume, "_close": close})
        rows.sort(key=lambda x: x["_dt"])
        return rows[-self.LOOKBACK_MINUTES :]

    def analyze(
        self,
        ticker,
        class_code,
        direction,
        entry_trigger,
        trading_date=None,
        session=None,
        now=None,
    ):
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return self.empty("NO_DIRECTION")
        trading_date = trading_date or self.session_service.get_trading_day()
        session = session or self.session_service.get_session()
        candles = self._load(ticker, class_code, session, trading_date, now=now)
        if len(candles) < self.MIN_CANDLES:
            return self.empty("NOT_ENOUGH_M1_CANDLES")

        trigger = self._f(entry_trigger)
        if trigger <= 0:
            return self.empty("NO_M5_TRIGGER")

        last = candles[-1]
        baseline = candles[:-1][-self.BASELINE_CANDLES :]
        if len(baseline) < 3:
            return self.empty("NO_VOLUME_BASELINE")

        baseline_values = [x["_volume"] for x in baseline if x["_volume"] > 0]
        if not baseline_values:
            return self.empty("NO_VOLUME_BASELINE")

        baseline_volume = median(baseline_values)
        volume_ratio = last["_volume"] / baseline_volume if baseline_volume > 0 else 0.0
        volume_confirmed = volume_ratio >= self.MIN_VOLUME_RATIO

        if direction == "LONG":
            price_triggered = last["_close"] >= trigger
        else:
            price_triggered = last["_close"] <= trigger

        if price_triggered and volume_confirmed:
            state = "CONFIRMED"
        elif price_triggered:
            state = "ARMED"
        else:
            state = "WAIT"

        return {
            "m1_entry_state": state,
            "m1_volume_state": "CONFIRMED" if volume_confirmed else "NORMAL",
            "m1_volume_ratio": round(volume_ratio, 2),
            "m1_entry_triggered": bool(price_triggered and volume_confirmed),
            "m1_candle_count": len(candles),
            "m1_last_price": round(last["_close"], 8),
            "m1_last_money_volume": round(last["_volume"], 2),
            "m1_volume_baseline": round(baseline_volume, 2),
            "m1_entry_trigger": round(trigger, 8),
            "m1_reason": (
                "M1_PRICE_AND_VOLUME_CONFIRMED"
                if price_triggered and volume_confirmed
                else "M1_PRICE_TRIGGERED_WAITING_VOLUME"
                if price_triggered
                else "M1_WAITING_FOR_TRIGGER"
            ),
        }
