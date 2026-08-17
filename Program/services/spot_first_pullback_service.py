"""SPOT-first pullback/rebound detector for the Trader_7_12 radar.

The service never produces an order. It answers a narrower question:
"Is the SPOT currently showing the kind of first pullback/rebound that is
worth watching, and which futures contract should inherit that idea?"
"""

from datetime import datetime, time, timedelta, timezone


class SpotFirstPullbackService:
    VERSION = "0.1"
    TIMEFRAME_MINUTES = 5
    MIN_IMPULSE_CANDLES = 2
    MIN_IMPULSE_PERCENT = 0.30
    RETRACEMENT_MIN = 0.35
    RETRACEMENT_IDEAL = 0.50
    RETRACEMENT_MAX = 0.75
    CONSOLIDATION_MAX_CANDLES = 5

    SESSION_WINDOWS = {
        "MORNING": (time(7, 0), time(10, 0)),
        "MAIN": (time(10, 0), time(19, 0)),
        "EVENING": (time(19, 0), time(23, 50)),
    }

    def __init__(self, history_service, session_service):
        self.history_service = history_service
        self.session_service = session_service

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_moscow(history_service, value):
        return history_service.to_moscow(value)

    def _window(self, session, trading_date):
        start, end = self.SESSION_WINDOWS.get(session, (None, None))
        if start is None:
            return None, None
        tz = self.history_service.MOSCOW_TZ
        return (
            datetime.combine(trading_date, start, tzinfo=tz),
            datetime.combine(trading_date, end, tzinfo=tz),
        )

    def load_session_candles(self, ticker, class_code, session=None, trading_date=None):
        session = session or self.session_service.get_session()
        trading_date = trading_date or self.session_service.get_trading_day()
        start_moscow, end_moscow = self._window(session, trading_date)
        if start_moscow is None:
            return []
        candles = self.history_service.load(
            ticker,
            class_code,
            start_time=start_moscow.astimezone(timezone.utc),
            end_time=end_moscow.astimezone(timezone.utc),
            timeframe_minutes=self.TIMEFRAME_MINUTES,
        )
        result = []
        for candle in candles or []:
            dt = self._to_moscow(self.history_service, candle.get("time"))
            if dt is None or not (start_moscow.time() <= dt.time() < end_moscow.time()):
                continue
            if self._float(candle.get("close")) <= 0:
                continue
            if self._float(candle.get("high")) < self._float(candle.get("low")):
                continue
            result.append(candle)
        result.sort(key=lambda item: self._to_moscow(self.history_service, item.get("time")) or datetime.min.replace(tzinfo=self.history_service.MOSCOW_TZ))
        return result

    def _empty(self, direction="NONE", reason="NO_SETUP"):
        return {
            "setup": "NONE",
            "setup_direction": direction,
            "setup_state": "WAIT",
            "setup_phase": reason,
            "setup_quality_score": 0.0,
            "impulse_percent": 0.0,
            "retracement_percent": 0.0,
            "retracement_ratio": 0.0,
            "consolidation_candles": 0,
            "entry_trigger": 0.0,
            "previous_high": 0.0,
            "previous_low": 0.0,
            "impulse_high": 0.0,
            "impulse_low": 0.0,
        }

    def _result(self, direction, setup, state, phase, quality, impulse_percent,
                retracement_percent, consolidation_candles, trigger, high, low,
                impulse_high, impulse_low):
        return {
            "setup": setup,
            "setup_direction": direction,
            "setup_state": state,
            "setup_phase": phase,
            "setup_quality_score": round(max(0.0, min(100.0, quality)), 1),
            "impulse_percent": round(impulse_percent, 3),
            "retracement_percent": round(retracement_percent, 3),
            "retracement_ratio": round(retracement_percent / 100.0, 3),
            "consolidation_candles": consolidation_candles,
            "entry_trigger": round(trigger, 8),
            "previous_high": round(high, 8),
            "previous_low": round(low, 8),
            "impulse_high": round(impulse_high, 8),
            "impulse_low": round(impulse_low, 8),
        }

    def _detect_long(self, candles):
        if len(candles) < self.MIN_IMPULSE_CANDLES + 2:
            return self._empty("LONG", "NOT_ENOUGH_CANDLES")

        for end in range(self.MIN_IMPULSE_CANDLES, len(candles)):
            start = end - self.MIN_IMPULSE_CANDLES
            impulse_open = self._float(candles[start].get("open"))
            impulse_high = max(self._float(c.get("high")) for c in candles[start:end])
            impulse_low = min(self._float(c.get("low")) for c in candles[start:end])
            impulse_close = self._float(candles[end - 1].get("close"))
            if impulse_open <= 0:
                continue
            impulse_percent = (impulse_close - impulse_open) / impulse_open * 100.0
            if impulse_percent < self.MIN_IMPULSE_PERCENT:
                continue

            pullback_start = end
            pullback_low = self._float(candles[end].get("low"))
            pullback_high = self._float(candles[end].get("high"))
            for p in range(pullback_start, min(len(candles), pullback_start + self.CONSOLIDATION_MAX_CANDLES + 2)):
                candle = candles[p]
                close = self._float(candle.get("close"))
                pullback_low = min(pullback_low, self._float(candle.get("low")))
                pullback_high = max(pullback_high, self._float(candle.get("high")))
                retracement = (impulse_high - pullback_low) / max(impulse_high - impulse_low, 1e-12) * 100.0
                if retracement < self.RETRACEMENT_MIN * 100:
                    continue
                if retracement > self.RETRACEMENT_MAX * 100:
                    break

                consolidation = p - pullback_start + 1
                quality = 55.0
                quality += max(0.0, 20.0 - abs(retracement - self.RETRACEMENT_IDEAL * 100.0) * 0.7)
                quality += min(15.0, impulse_percent * 8.0)
                quality += min(10.0, consolidation * 2.0)

                if close > pullback_high and p > pullback_start:
                    return self._result("LONG", "FIRST_PULLBACK", "CONFIRMED", "BREAKOUT_AFTER_PULLBACK", quality + 8, impulse_percent, retracement, consolidation, pullback_high, pullback_high, pullback_low, impulse_high, impulse_low)

                if consolidation >= 2:
                    return self._result("LONG", "FIRST_PULLBACK", "WATCH", "PULLBACK_CONSOLIDATION", quality, impulse_percent, retracement, consolidation, pullback_high, pullback_high, pullback_low, impulse_high, impulse_low)

                return self._result("LONG", "FIRST_PULLBACK", "WATCH", "FIRST_PULLBACK", quality, impulse_percent, retracement, consolidation, pullback_high, pullback_high, pullback_low, impulse_high, impulse_low)
        return self._empty("LONG")

    def _detect_short(self, candles):
        if len(candles) < self.MIN_IMPULSE_CANDLES + 2:
            return self._empty("SHORT", "NOT_ENOUGH_CANDLES")

        for end in range(self.MIN_IMPULSE_CANDLES, len(candles)):
            start = end - self.MIN_IMPULSE_CANDLES
            impulse_open = self._float(candles[start].get("open"))
            impulse_low = min(self._float(c.get("low")) for c in candles[start:end])
            impulse_high = max(self._float(c.get("high")) for c in candles[start:end])
            impulse_close = self._float(candles[end - 1].get("close"))
            if impulse_open <= 0:
                continue
            impulse_percent = (impulse_close - impulse_open) / impulse_open * 100.0
            if impulse_percent > -self.MIN_IMPULSE_PERCENT:
                continue

            rebound_start = end
            rebound_high = self._float(candles[end].get("high"))
            rebound_low = self._float(candles[end].get("low"))
            for p in range(rebound_start, min(len(candles), rebound_start + self.CONSOLIDATION_MAX_CANDLES + 2)):
                candle = candles[p]
                close = self._float(candle.get("close"))
                rebound_high = max(rebound_high, self._float(candle.get("high")))
                rebound_low = min(rebound_low, self._float(candle.get("low")))
                retracement = (rebound_high - impulse_low) / max(impulse_high - impulse_low, 1e-12) * 100.0
                if retracement < self.RETRACEMENT_MIN * 100:
                    continue
                if retracement > self.RETRACEMENT_MAX * 100:
                    break

                consolidation = p - rebound_start + 1
                quality = 55.0
                quality += max(0.0, 20.0 - abs(retracement - self.RETRACEMENT_IDEAL * 100.0) * 0.7)
                quality += min(15.0, abs(impulse_percent) * 8.0)
                quality += min(10.0, consolidation * 2.0)

                if close < rebound_low and p > rebound_start:
                    return self._result("SHORT", "FIRST_REBOUND", "CONFIRMED", "BREAKDOWN_AFTER_REBOUND", quality + 8, impulse_percent, retracement, consolidation, rebound_low, rebound_high, rebound_low, impulse_high, impulse_low)

                if consolidation >= 2:
                    return self._result("SHORT", "FIRST_REBOUND", "WATCH", "REBOUND_CONSOLIDATION", quality, impulse_percent, retracement, consolidation, rebound_low, rebound_high, rebound_low, impulse_high, impulse_low)

                return self._result("SHORT", "FIRST_REBOUND", "WATCH", "FIRST_REBOUND", quality, impulse_percent, retracement, consolidation, rebound_low, rebound_high, rebound_low, impulse_high, impulse_low)
        return self._empty("SHORT")

    def analyze(self, ticker, class_code, direction=None, session=None, trading_date=None):
        session = session or self.session_service.get_session()
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return self._empty("NONE", "NO_DIRECTION")
        candles = self.load_session_candles(ticker, class_code, session=session, trading_date=trading_date)
        if not candles:
            return self._empty(direction, "NO_SESSION_CANDLES")
        result = self._detect_long(candles) if direction == "LONG" else self._detect_short(candles)
        result["setup_session"] = session
        result["setup_candle_count"] = len(candles)
        return result
