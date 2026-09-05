"""Trader_7_12 Pro — canonical completed-D1 trend profile.

The scanner's directional idea starts on the daily timeframe. This service
measures the last 2–3 completed daily candles and deliberately avoids any
futures data or trading decisions.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class DailyTrendProfileService:
    """Deterministic, network-free analysis of completed daily candles."""

    VERSION = "2.1"
    MIN_DAYS = 2
    MAX_DAYS = 3
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    @staticmethod
    def _f(candle, key):
        try:
            value = float(candle.get(key, 0) or 0)
        except (AttributeError, TypeError, ValueError):
            return 0.0
        return value if value > 0 else 0.0

    @classmethod
    def _date_key(cls, candle):
        """Return the candle's Moscow trading date; never guess from position."""
        if not isinstance(candle, dict):
            return None
        value = candle.get("time") or candle.get("date") or candle.get("trading_date")
        if value is None:
            return None
        if hasattr(value, "date") and not isinstance(value, str):
            try:
                if getattr(value, "tzinfo", None) is None:
                    value = value.replace(tzinfo=timezone.utc)
                return value.astimezone(cls.MOSCOW_TZ).date()
            except (AttributeError, ValueError, TypeError):
                return None
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(cls.MOSCOW_TZ).date()
        except (TypeError, ValueError):
            try:
                return datetime.fromisoformat(text[:10]).date()
            except (TypeError, ValueError):
                return None

    @classmethod
    def _completed(cls, candles, before_date=None):
        if not isinstance(candles, list):
            return []
        output = []
        seen_dates = set()
        for candle in candles:
            if not isinstance(candle, dict):
                continue
            day = cls._date_key(candle)
            if day is None or (before_date is not None and day >= before_date):
                continue
            if day in seen_dates:
                continue
            seen_dates.add(day)
            output.append((day, candle))
        output.sort(key=lambda pair: pair[0])
        return [candle for _, candle in output]

    @classmethod
    def _window(cls, candles, before_date=None):
        valid = cls._completed(candles, before_date=before_date)
        return valid[-cls.MAX_DAYS:] if len(valid) >= cls.MIN_DAYS else []

    @classmethod
    def _structure(cls, candles, before_date=None):
        selected = cls._window(candles, before_date=before_date)
        if len(selected) < cls.MIN_DAYS:
            return {"state": "INSUFFICIENT_DATA", "direction": "NEUTRAL", "days": len(selected),
                    "green_days": 0, "red_days": 0, "rising_highs": False, "rising_lows": False,
                    "falling_highs": False, "falling_lows": False, "return_percent": 0.0}

        opens = [cls._f(c, "open") for c in selected]
        closes = [cls._f(c, "close") for c in selected]
        highs = [cls._f(c, "high") for c in selected]
        lows = [cls._f(c, "low") for c in selected]
        if any(v <= 0 for values in (opens, closes, highs, lows) for v in values):
            return {"state": "INVALID_DATA", "direction": "NEUTRAL", "days": len(selected),
                    "green_days": 0, "red_days": 0, "rising_highs": False, "rising_lows": False,
                    "falling_highs": False, "falling_lows": False, "return_percent": 0.0}

        green_days = sum(1 for o, c in zip(opens, closes) if c > o)
        red_days = sum(1 for o, c in zip(opens, closes) if c < o)
        rising_highs = all(a < b for a, b in zip(highs, highs[1:]))
        rising_lows = all(a < b for a, b in zip(lows, lows[1:]))
        falling_highs = all(a > b for a, b in zip(highs, highs[1:]))
        falling_lows = all(a > b for a, b in zip(lows, lows[1:]))
        return_percent = (closes[-1] / closes[0] - 1.0) * 100.0
        strong = green_days == len(selected) and rising_highs and rising_lows
        weak = red_days == len(selected) and falling_highs and falling_lows
        direction = "LONG" if strong else "SHORT" if weak else "NEUTRAL"
        state = "STRONG_STRUCTURE" if strong else "WEAK_STRUCTURE" if weak else "MIXED"
        return {"state": state, "direction": direction, "days": len(selected), "green_days": green_days,
                "red_days": red_days, "rising_highs": rising_highs, "rising_lows": rising_lows,
                "falling_highs": falling_highs, "falling_lows": falling_lows,
                "return_percent": round(return_percent, 2)}

    @classmethod
    def _daily_relative_returns(cls, asset_candles, benchmark_candles, days, before_date=None):
        """Compare matching Moscow trading dates; positional alignment is forbidden."""
        assets = cls._window(asset_candles, before_date=before_date)
        markets = cls._window(benchmark_candles, before_date=before_date)
        if len(assets) != days or len(markets) != days:
            return []

        asset_by_date = {cls._date_key(c): c for c in assets}
        market_by_date = {cls._date_key(c): c for c in markets}
        common_dates = sorted(set(asset_by_date) & set(market_by_date))
        if len(common_dates) != days:
            return []

        output = []
        for day in common_dates:
            asset, market = asset_by_date[day], market_by_date[day]
            ao, ac = cls._f(asset, "open"), cls._f(asset, "close")
            mo, mc = cls._f(market, "open"), cls._f(market, "close")
            if min(ao, ac, mo, mc) <= 0:
                return []
            asset_return = (ac / ao - 1.0) * 100.0
            market_return = (mc / mo - 1.0) * 100.0
            output.append({"date": day.isoformat(), "asset_return": round(asset_return, 4),
                           "benchmark_return": round(market_return, 4),
                           "relative_strength": round(asset_return - market_return, 4)})
        return output

    @classmethod
    def analyze(cls, candles, benchmark_candles=None, before_date=None):
        """Return D1 structure plus market-relative confirmation on completed dates."""
        structure = cls._structure(candles, before_date=before_date)
        days = structure["days"]
        daily_relative = cls._daily_relative_returns(candles, benchmark_candles, days, before_date=before_date) if benchmark_candles else []

        relative_direction = "UNAVAILABLE"
        relative_mean = 0.0
        relative_consistent = False
        if daily_relative:
            values = [x["relative_strength"] for x in daily_relative]
            relative_mean = sum(values) / len(values)
            relative_consistent = all(x > 0 for x in values) or all(x < 0 for x in values)
            if relative_consistent:
                relative_direction = "STRONGER" if all(x > 0 for x in values) else "WEAKER"
            else:
                relative_direction = "MIXED"

        confirmed_direction = "NEUTRAL"
        if structure["direction"] == "LONG" and relative_direction == "STRONGER":
            confirmed_direction = "LONG"
        elif structure["direction"] == "SHORT" and relative_direction == "WEAKER":
            confirmed_direction = "SHORT"

        return {"version": cls.VERSION, "direction": confirmed_direction,
                "structure_direction": structure["direction"], "structure_state": structure["state"],
                "days": days, "green_days": structure["green_days"], "red_days": structure["red_days"],
                "rising_highs": structure["rising_highs"], "rising_lows": structure["rising_lows"],
                "falling_highs": structure["falling_highs"], "falling_lows": structure["falling_lows"],
                "return_percent": structure["return_percent"], "relative_direction": relative_direction,
                "relative_mean_pp": round(relative_mean, 4), "relative_consistent": relative_consistent,
                "daily_relative": daily_relative, "qualified": confirmed_direction in {"LONG", "SHORT"}}
