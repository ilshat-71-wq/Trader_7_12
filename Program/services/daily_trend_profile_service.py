"""
Trader_7_12 Pro — Daily Trend Profile

Deterministic, network-free analysis of completed daily SPOT candles.

Purpose:
- explicitly measure 2/3/4-day directional persistence;
- distinguish a persistent trend from a one-day impulse;
- expose direction, consistency, return and a bounded trend score;
- provide a reusable input for the future TOP-2/3 opportunity assistant.

The service never uses futures data and never makes a trade decision.
"""


class DailyTrendProfileService:
    """Analyze completed daily candles without network access."""

    VERSION = "1.0"
    WINDOWS = (2, 3, 4)

    @staticmethod
    def _close(candle):
        try:
            value = float(candle.get("close", 0) or 0)
        except (AttributeError, TypeError, ValueError):
            return 0.0
        return value if value > 0 else 0.0

    @classmethod
    def _window(cls, candles, days):
        if not isinstance(candles, list):
            return []
        return candles[-days:] if len(candles) >= days else []

    @classmethod
    def _measure(cls, candles, days):
        selected = cls._window(candles, days)
        if len(selected) < days:
            return {
                "days": days,
                "direction": "NEUTRAL",
                "state": "INSUFFICIENT_DATA",
                "change_percent": 0.0,
                "positive_days": 0,
                "negative_days": 0,
                "directional_days": 0,
                "consistency_percent": 0.0,
            }

        closes = [cls._close(candle) for candle in selected]
        if any(value <= 0 for value in closes):
            return {
                "days": days,
                "direction": "NEUTRAL",
                "state": "INVALID_DATA",
                "change_percent": 0.0,
                "positive_days": 0,
                "negative_days": 0,
                "directional_days": 0,
                "consistency_percent": 0.0,
            }

        first_close = closes[0]
        last_close = closes[-1]
        change_percent = (last_close - first_close) / first_close * 100.0

        positive_days = 0
        negative_days = 0
        for previous, current in zip(closes, closes[1:]):
            if current > previous:
                positive_days += 1
            elif current < previous:
                negative_days += 1

        directional_days = max(positive_days, negative_days)
        comparisons = max(days - 1, 1)
        consistency = directional_days / comparisons * 100.0

        if change_percent > 0 and positive_days > negative_days:
            direction = "LONG"
        elif change_percent < 0 and negative_days > positive_days:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"

        if direction == "NEUTRAL":
            state = "MIXED"
        elif consistency >= 100.0:
            state = "PERSISTENT"
        elif consistency >= 66.67:
            state = "CONSISTENT"
        else:
            state = "WEAK"

        return {
            "days": days,
            "direction": direction,
            "state": state,
            "change_percent": round(change_percent, 2),
            "positive_days": positive_days,
            "negative_days": negative_days,
            "directional_days": directional_days,
            "consistency_percent": round(consistency, 2),
        }

    @classmethod
    def analyze(cls, candles):
        """Return 2/3/4-day profiles and a conservative aggregate."""
        profiles = {
            str(days): cls._measure(candles, days)
            for days in cls.WINDOWS
        }

        valid = [
            profile
            for profile in profiles.values()
            if profile["state"] not in {"INSUFFICIENT_DATA", "INVALID_DATA"}
        ]

        directions = [
            profile["direction"]
            for profile in valid
            if profile["direction"] in {"LONG", "SHORT"}
        ]

        if not directions:
            aggregate_direction = "NEUTRAL"
        elif directions.count("LONG") > directions.count("SHORT"):
            aggregate_direction = "LONG"
        elif directions.count("SHORT") > directions.count("LONG"):
            aggregate_direction = "SHORT"
        else:
            aggregate_direction = "NEUTRAL"

        aligned = sum(
            1 for direction in directions
            if direction == aggregate_direction
        )
        alignment_percent = (
            round(aligned / len(directions) * 100.0, 2)
            if directions and aggregate_direction != "NEUTRAL"
            else 0.0
        )

        persistent_windows = sum(
            1
            for profile in valid
            if profile["direction"] == aggregate_direction
            and profile["state"] == "PERSISTENT"
        )

        # Conservative bounded score. Persistence and cross-window agreement
        # matter more than raw price change, so a single shock candle cannot
        # dominate the profile.
        score = min(
            100,
            persistent_windows * 20
            + round(alignment_percent * 0.30)
            + round(
                max(
                    (abs(profiles["4"]["change_percent"])
                     if profiles["4"]["state"] not in {"INSUFFICIENT_DATA", "INVALID_DATA"}
                     else 0.0),
                    (abs(profiles["3"]["change_percent"])
                     if profiles["3"]["state"] not in {"INSUFFICIENT_DATA", "INVALID_DATA"}
                     else 0.0),
                ) * 5
            ),
        )

        return {
            "version": cls.VERSION,
            "direction": aggregate_direction,
            "alignment_percent": alignment_percent,
            "persistent_windows": persistent_windows,
            "score": score,
            "windows": profiles,
        }
