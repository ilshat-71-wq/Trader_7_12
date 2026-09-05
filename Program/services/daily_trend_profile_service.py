"""Trader_7_12 Pro — canonical completed-D1 trend profile.

The scanner's directional idea starts on the daily timeframe. This service
measures the last 2–3 completed daily candles and deliberately avoids any
futures data or trading decisions.

Strong (LONG context):
- green daily candles;
- rising highs AND rising lows;
- the asset outperforms the market on the same daily observations.

Weak (SHORT context):
- red daily candles;
- falling highs AND falling lows;
- the asset underperforms the market on the same daily observations.
"""


class DailyTrendProfileService:
    """Deterministic, network-free analysis of completed daily candles."""

    VERSION = "2.0"
    MIN_DAYS = 2
    MAX_DAYS = 3

    @staticmethod
    def _f(candle, key):
        try:
            value = float(candle.get(key, 0) or 0)
        except (AttributeError, TypeError, ValueError):
            return 0.0
        return value if value > 0 else 0.0

    @classmethod
    def _window(cls, candles):
        if not isinstance(candles, list):
            return []
        valid = [c for c in candles if isinstance(c, dict)]
        return valid[-cls.MAX_DAYS:] if len(valid) >= cls.MIN_DAYS else []

    @classmethod
    def _structure(cls, candles):
        """Return the D1 candle structure required by the project idea."""
        selected = cls._window(candles)
        if len(selected) < cls.MIN_DAYS:
            return {
                "state": "INSUFFICIENT_DATA",
                "direction": "NEUTRAL",
                "days": len(selected),
                "green_days": 0,
                "red_days": 0,
                "rising_highs": False,
                "rising_lows": False,
                "falling_highs": False,
                "falling_lows": False,
                "return_percent": 0.0,
            }

        opens = [cls._f(c, "open") for c in selected]
        closes = [cls._f(c, "close") for c in selected]
        highs = [cls._f(c, "high") for c in selected]
        lows = [cls._f(c, "low") for c in selected]
        if any(v <= 0 for values in (opens, closes, highs, lows) for v in values):
            return {
                "state": "INVALID_DATA",
                "direction": "NEUTRAL",
                "days": len(selected),
                "green_days": 0,
                "red_days": 0,
                "rising_highs": False,
                "rising_lows": False,
                "falling_highs": False,
                "falling_lows": False,
                "return_percent": 0.0,
            }

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
        return {
            "state": state,
            "direction": direction,
            "days": len(selected),
            "green_days": green_days,
            "red_days": red_days,
            "rising_highs": rising_highs,
            "rising_lows": rising_lows,
            "falling_highs": falling_highs,
            "falling_lows": falling_lows,
            "return_percent": round(return_percent, 2),
        }

    @staticmethod
    def _daily_relative_returns(asset_candles, benchmark_candles, days):
        """Compare same-day asset and benchmark returns, oldest to newest."""
        if not isinstance(asset_candles, list) or not isinstance(benchmark_candles, list):
            return []
        assets = [c for c in asset_candles if isinstance(c, dict)][-days:]
        benchmark = [c for c in benchmark_candles if isinstance(c, dict)][-days:]
        if len(assets) != days or len(benchmark) != days:
            return []
        output = []
        for asset, market in zip(assets, benchmark):
            ao, ac = DailyTrendProfileService._f(asset, "open"), DailyTrendProfileService._f(asset, "close")
            mo, mc = DailyTrendProfileService._f(market, "open"), DailyTrendProfileService._f(market, "close")
            if min(ao, ac, mo, mc) <= 0:
                return []
            asset_return = (ac / ao - 1.0) * 100.0
            market_return = (mc / mo - 1.0) * 100.0
            output.append({
                "asset_return": round(asset_return, 4),
                "benchmark_return": round(market_return, 4),
                "relative_strength": round(asset_return - market_return, 4),
            })
        return output

    @classmethod
    def analyze(cls, candles, benchmark_candles=None):
        """Return canonical D1 structure plus market-relative confirmation."""
        structure = cls._structure(candles)
        days = structure["days"]
        daily_relative = cls._daily_relative_returns(candles, benchmark_candles, days) if benchmark_candles else []

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

        return {
            "version": cls.VERSION,
            "direction": confirmed_direction,
            "structure_direction": structure["direction"],
            "structure_state": structure["state"],
            "days": days,
            "green_days": structure["green_days"],
            "red_days": structure["red_days"],
            "rising_highs": structure["rising_highs"],
            "rising_lows": structure["rising_lows"],
            "falling_highs": structure["falling_highs"],
            "falling_lows": structure["falling_lows"],
            "return_percent": structure["return_percent"],
            "relative_direction": relative_direction,
            "relative_mean_pp": round(relative_mean, 4),
            "relative_consistent": relative_consistent,
            "daily_relative": daily_relative,
            "qualified": confirmed_direction in {"LONG", "SHORT"},
        }
