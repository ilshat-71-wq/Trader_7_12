"""SPOT-first impulse -> H1 structure -> first pullback/rebound detector."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


class SpotFirstPullbackService:
    VERSION = "0.3"
    TIMEFRAME_MINUTES = 5
    H1_TIMEFRAME_MINUTES = 60
    H1_LOOKBACK_DAYS = 10
    MIN_IMPULSE_CANDLES = 2
    MIN_IMPULSE_PERCENT = 0.30
    RETRACEMENT_MIN = 0.35
    RETRACEMENT_IDEAL = 0.50
    RETRACEMENT_MAX = 0.75
    CONSOLIDATION_MAX_CANDLES = 5
    H1_LEVEL_TOLERANCE_PERCENT = 0.80

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
            ticker, class_code,
            start_time=start_moscow.astimezone(ZoneInfo("UTC")),
            end_time=end_moscow.astimezone(ZoneInfo("UTC")),
            timeframe_minutes=self.TIMEFRAME_MINUTES,
        )
        result = []
        for candle in candles or []:
            dt = self.history_service.to_moscow(candle.get("time"))
            if dt is None or not (start_moscow.time() <= dt.time() < end_moscow.time()):
                continue
            if self._float(candle.get("close")) <= 0:
                continue
            if self._float(candle.get("high")) < self._float(candle.get("low")):
                continue
            result.append(candle)
        result.sort(key=lambda item: self.history_service.to_moscow(item.get("time")) or datetime.min.replace(tzinfo=self.history_service.MOSCOW_TZ))
        return result

    def load_h1_candles(self, ticker, class_code, trading_date=None):
        """Load recent SPOT H1 candles used only for structural level context."""
        trading_date = trading_date or self.session_service.get_trading_day()
        if trading_date is None:
            return []
        tz = self.history_service.MOSCOW_TZ
        start_moscow = datetime.combine(trading_date, time(0, 0), tzinfo=tz)
        start_moscow = start_moscow.replace(day=max(1, start_moscow.day))
        start_utc = start_moscow.astimezone(timezone.utc)
        end_utc = self.history_service.now().astimezone(timezone.utc)
        candles = self.history_service.load(
            ticker, class_code,
            start_time=start_utc,
            end_time=end_utc,
            timeframe_minutes=self.H1_TIMEFRAME_MINUTES,
        )
        result = []
        for candle in candles or []:
            dt = self.history_service.to_moscow(candle.get("time"))
            high = self._float(candle.get("high"))
            low = self._float(candle.get("low"))
            close = self._float(candle.get("close"))
            if dt is None or close <= 0 or high <= 0 or low <= 0 or high < low:
                continue
            result.append(candle)
        result.sort(key=lambda item: self.history_service.to_moscow(item.get("time")) or datetime.min.replace(tzinfo=tz))
        return result[-24 * self.H1_LOOKBACK_DAYS:]

    def _h1_context(self, ticker, class_code, spot_price, trading_date=None):
        """Find nearest H1 support/resistance around current SPOT price."""
        price = self._float(spot_price)
        empty = {
            "h1_support": 0.0,
            "h1_resistance": 0.0,
            "h1_nearest_level": 0.0,
            "h1_nearest_level_type": "NONE",
            "h1_level_distance_percent": 0.0,
            "h1_level_context": "UNAVAILABLE",
            "h1_candle_count": 0,
        }
        if price <= 0:
            return empty
        try:
            candles = self.load_h1_candles(ticker, class_code, trading_date=trading_date)
        except Exception:
            return empty
        if not candles:
            return empty

        supports = []
        resistances = []
        for candle in candles:
            high = self._float(candle.get("high"))
            low = self._float(candle.get("low"))
            if 0 < low <= price:
                supports.append(low)
            if high >= price:
                resistances.append(high)

        support = max(supports) if supports else 0.0
        resistance = min(resistances) if resistances else 0.0
        support_distance = ((price - support) / price * 100.0) if support else 999.0
        resistance_distance = ((resistance - price) / price * 100.0) if resistance else 999.0

        if support and support_distance <= resistance_distance:
            nearest, level_type, distance = support, "SUPPORT", support_distance
        elif resistance:
            nearest, level_type, distance = resistance, "RESISTANCE", resistance_distance
        else:
            nearest, level_type, distance = 0.0, "NONE", 0.0

        if level_type == "SUPPORT" and distance <= self.H1_LEVEL_TOLERANCE_PERCENT:
            context = "NEAR_H1_SUPPORT"
        elif level_type == "RESISTANCE" and distance <= self.H1_LEVEL_TOLERANCE_PERCENT:
            context = "NEAR_H1_RESISTANCE"
        else:
            context = "BETWEEN_H1_LEVELS"

        return {
            "h1_support": round(support, 8),
            "h1_resistance": round(resistance, 8),
            "h1_nearest_level": round(nearest, 8),
            "h1_nearest_level_type": level_type,
            "h1_level_distance_percent": round(distance, 3) if distance < 999 else 0.0,
            "h1_level_context": context,
            "h1_candle_count": len(candles),
        }

    @staticmethod
    def _empty(direction="NONE", reason="NO_SETUP"):
        return {
            "setup": "NONE", "setup_direction": direction, "setup_state": "WAIT",
            "setup_phase": reason, "setup_quality_score": 0.0,
            "impulse_percent": 0.0, "retracement_percent": 0.0, "retracement_ratio": 0.0,
            "consolidation_candles": 0, "entry_trigger": 0.0,
            "previous_high": 0.0, "previous_low": 0.0,
            "impulse_high": 0.0, "impulse_low": 0.0,
            "h1_support": 0.0, "h1_resistance": 0.0,
            "h1_nearest_level": 0.0, "h1_nearest_level_type": "NONE",
            "h1_level_distance_percent": 0.0, "h1_level_context": "UNAVAILABLE",
            "h1_candle_count": 0, "h1_level_bonus": 0.0,
        }

    def _result(self, direction, state, phase, quality, impulse_percent, retracement_percent,
                consolidation, trigger, high, low, impulse_high, impulse_low):
        return {
            "setup": "FIRST_PULLBACK" if direction == "LONG" else "FIRST_REBOUND",
            "setup_direction": direction, "setup_state": state, "setup_phase": phase,
            "setup_quality_score": round(max(0.0, min(100.0, quality)), 1),
            "impulse_percent": round(impulse_percent, 3),
            "retracement_percent": round(retracement_percent, 3),
            "retracement_ratio": round(retracement_percent / 100.0, 3),
            "consolidation_candles": consolidation,
            "entry_trigger": round(trigger, 8),
            "previous_high": round(high, 8), "previous_low": round(low, 8),
            "impulse_high": round(impulse_high, 8), "impulse_low": round(impulse_low, 8),
        }

    def _quality(self, impulse_percent, retracement, consolidation):
        score = 55.0
        score += max(0.0, 20.0 - abs(retracement - 50.0) * 0.7)
        score += min(15.0, abs(impulse_percent) * 8.0)
        score += min(10.0, consolidation * 2.0)
        return score

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
            pullback_low = self._float(candles[end].get("low"))
            pullback_high = self._float(candles[end].get("high"))
            consolidation = 0
            for p in range(end, min(len(candles), end + self.CONSOLIDATION_MAX_CANDLES + 2)):
                candle = candles[p]
                prior_high = pullback_high
                pullback_low = min(pullback_low, self._float(candle.get("low")))
                retracement = (impulse_high - pullback_low) / max(impulse_high - impulse_low, 1e-12) * 100.0
                if retracement > self.RETRACEMENT_MAX * 100:
                    break
                if retracement < self.RETRACEMENT_MIN * 100:
                    pullback_high = max(pullback_high, self._float(candle.get("high")))
                    continue
                consolidation += 1
                quality = self._quality(impulse_percent, retracement, consolidation)
                close = self._float(candle.get("close"))
                if p > end and close > prior_high:
                    return self._result("LONG", "CONFIRMED", "BREAKOUT_AFTER_PULLBACK", quality + 8, impulse_percent, retracement, consolidation, prior_high, prior_high, pullback_low, impulse_high, impulse_low)
                if consolidation >= 2:
                    return self._result("LONG", "WATCH", "PULLBACK_CONSOLIDATION", quality, impulse_percent, retracement, consolidation, prior_high, prior_high, pullback_low, impulse_high, impulse_low)
                pullback_high = max(pullback_high, self._float(candle.get("high")))
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
            rebound_high = self._float(candles[end].get("high"))
            rebound_low = self._float(candles[end].get("low"))
            consolidation = 0
            for p in range(end, min(len(candles), end + self.CONSOLIDATION_MAX_CANDLES + 2)):
                candle = candles[p]
                prior_low = rebound_low
                rebound_high = max(rebound_high, self._float(candle.get("high")))
                retracement = (rebound_high - impulse_low) / max(impulse_high - impulse_low, 1e-12) * 100.0
                if retracement > self.RETRACEMENT_MAX * 100:
                    break
                if retracement < self.RETRACEMENT_MIN * 100:
                    rebound_low = min(rebound_low, self._float(candle.get("low")))
                    continue
                consolidation += 1
                quality = self._quality(impulse_percent, retracement, consolidation)
                close = self._float(candle.get("close"))
                if p > end and close < prior_low:
                    return self._result("SHORT", "CONFIRMED", "BREAKDOWN_AFTER_REBOUND", quality + 8, impulse_percent, retracement, consolidation, prior_low, rebound_high, prior_low, impulse_high, impulse_low)
                if consolidation >= 2:
                    return self._result("SHORT", "WATCH", "REBOUND_CONSOLIDATION", quality, impulse_percent, retracement, consolidation, prior_low, rebound_high, prior_low, impulse_high, impulse_low)
                rebound_low = min(rebound_low, self._float(candle.get("low")))
        return self._empty("SHORT")

    def _apply_h1_context(self, result, h1_context, direction):
        result.update(h1_context)
        context = h1_context.get("h1_level_context", "UNAVAILABLE")
        distance = self._float(h1_context.get("h1_level_distance_percent"))
        bonus = 0.0
        if direction == "LONG" and context == "NEAR_H1_SUPPORT":
            bonus = max(0.0, 8.0 - distance * 4.0)
        elif direction == "SHORT" and context == "NEAR_H1_RESISTANCE":
            bonus = max(0.0, 8.0 - distance * 4.0)
        if bonus:
            result["setup_quality_score"] = round(min(100.0, self._float(result.get("setup_quality_score")) + bonus), 1)
        result["h1_level_bonus"] = round(bonus, 1)
        return result

    def analyze(self, ticker, class_code, direction=None, session=None, trading_date=None, spot_price=None):
        session = session or self.session_service.get_session()
        trading_date = trading_date or self.session_service.get_trading_day()
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return self._empty("NONE", "NO_DIRECTION")
        candles = self.load_session_candles(ticker, class_code, session=session, trading_date=trading_date)
        if not candles:
            result = self._empty(direction, "NO_SESSION_CANDLES")
        else:
            result = self._detect_long(candles) if direction == "LONG" else self._detect_short(candles)
        if spot_price is None and candles:
            spot_price = self._float(candles[-1].get("close"))
        h1_context = self._h1_context(ticker, class_code, spot_price, trading_date=trading_date)
        result = self._apply_h1_context(result, h1_context, direction)
        result["setup_session"] = session
        result["setup_candle_count"] = len(candles)
        return result
