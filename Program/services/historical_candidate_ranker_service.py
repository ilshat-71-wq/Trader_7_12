"""Lightweight ranking for read-only historical scanner validation."""

import math


class HistoricalCandidateRankerService:
    """Rank historical SPOT/FUTURES candidates without trade execution or risk sizing."""

    VERSION = "0.1"

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _liquidity_score(cls, value, floor=100_000_000.0, ceiling=1_000_000_000.0, weight=10.0):
        value = max(cls._float(value), 0.0)
        if value <= floor:
            return 0.0
        if value >= ceiling:
            return weight
        ratio = (math.log10(value) - math.log10(floor)) / (
            math.log10(ceiling) - math.log10(floor)
        )
        return round(max(0.0, min(1.0, ratio)) * weight, 2)

    @classmethod
    def score(cls, row):
        """Return a deterministic 0-100 score from already-loaded historical data."""
        confirmation = row.get("futures_confirmation") or {}
        confirmation_score = max(0.0, min(100.0, cls._float(confirmation.get("score"))))

        trend_state = str(row.get("trend_state") or "").upper()
        trend_score = {
            "UPTREND": 20.0,
            "DOWNTREND": 20.0,
            "WEAK_UPTREND": 12.0,
            "WEAK_DOWNTREND": 12.0,
        }.get(trend_state, 0.0)

        move = abs(cls._float(row.get("trend_change_percent")))
        move_score = min(move * 5.0, 15.0)

        setup = str(row.get("setup") or "NONE").upper()
        setup_score = {
            "BREAKOUT": 15.0,
            "PULLBACK": 13.0,
            "REBOUND": 13.0,
        }.get(setup, 5.0 if setup != "NONE" else 0.0)

        spot_liquidity_score = cls._liquidity_score(
            row.get("average_daily_money"), weight=10.0
        )
        futures_liquidity_score = cls._liquidity_score(
            row.get("futures_average_daily_money"), weight=5.0
        )

        score = (
            confirmation_score * 0.35
            + trend_score
            + move_score
            + setup_score
            + spot_liquidity_score
            + futures_liquidity_score
        )
        return round(min(score, 100.0), 2)

    @classmethod
    def rank(cls, rows, limit=None):
        if not isinstance(rows, list):
            return []

        ranked = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["candidate_score"] = cls.score(item)
            item["relative_strength"] = None
            item["relative_strength_available"] = False
            ranked.append(item)

        ranked.sort(
            key=lambda item: (
                item.get("candidate_score", 0.0),
                item.get("confirmation_time") is not None,
                item.get("confirmation_time") or "99:99",
                item.get("average_daily_money", 0.0),
            ),
            reverse=True,
        )

        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank

        if limit is not None:
            return ranked[:int(limit)]
        return ranked
