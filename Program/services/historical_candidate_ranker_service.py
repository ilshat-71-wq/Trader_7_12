"""Lightweight ranking for read-only historical scanner validation."""

import math


class HistoricalCandidateRankerService:
    """Rank historical candidates with SPOT readiness as the primary signal."""

    VERSION = "0.4"
    RS_SCORE_CAP = 15.0
    RS_EXCESS_CAP_PERCENT = 8.0

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
        ratio = (math.log10(value) - math.log10(floor)) / (math.log10(ceiling) - math.log10(floor))
        return round(max(0.0, min(1.0, ratio)) * weight, 2)

    @classmethod
    def _directional_rs_score(cls, row, direction):
        """Reward real excess return in the trade direction without early saturation."""
        if not row.get("relative_strength_available"):
            return 0.0

        data = row.get("relative_strength_data") or {}
        excess_percent = cls._float(data.get("excess_change_percent"), default=float("nan"))
        if math.isnan(excess_percent):
            raw_score = cls._float(row.get("relative_strength"))
            excess_percent = raw_score / 10.0

        directional_excess = excess_percent if direction == "LONG" else -excess_percent if direction == "SHORT" else 0.0
        capped = max(-cls.RS_EXCESS_CAP_PERCENT, min(cls.RS_EXCESS_CAP_PERCENT, directional_excess))
        return round((capped / cls.RS_EXCESS_CAP_PERCENT) * cls.RS_SCORE_CAP, 2)

    @classmethod
    def _spot_readiness_score(cls, row):
        """Score readiness from SPOT setup state only; futures confirmation is not a gate."""
        state = str(row.get("spot_setup_state") or row.get("setup_state") or "WAIT").upper()
        trigger = cls._float(row.get("spot_entry_trigger", row.get("entry_trigger")))
        ready_time = row.get("spot_ready_time", row.get("ready_time"))

        if state == "CONFIRMED" and trigger > 0:
            return 40.0
        if state == "READY" and trigger > 0:
            return 35.0
        if state == "WATCH" and trigger > 0:
            return 25.0
        if ready_time and trigger > 0:
            return 30.0
        if state != "WAIT":
            return 10.0
        return 0.0

    @classmethod
    def score(cls, row):
        direction = str(row.get("direction") or "").upper()
        trend_state = str(row.get("trend_state") or "").upper()
        trend_score = {"UPTREND": 12.0, "DOWNTREND": 12.0, "WEAK_UPTREND": 7.0, "WEAK_DOWNTREND": 7.0}.get(trend_state, 0.0)
        move_score = min(abs(cls._float(row.get("trend_change_percent"))) * 4.0, 10.0)
        rs_score = cls._directional_rs_score(row, direction)
        readiness_score = cls._spot_readiness_score(row)
        setup = str(row.get("setup") or "NONE").upper()
        setup_score = {"BREAKOUT": 13.0, "PULLBACK": 11.0, "REBOUND": 10.0, "FIRST_PULLBACK": 11.0, "FIRST_REBOUND": 10.0}.get(setup, 4.0 if setup != "NONE" else 0.0)
        spot_liquidity_score = cls._liquidity_score(row.get("average_daily_money"), weight=10.0)
        futures_liquidity_score = cls._liquidity_score(row.get("futures_average_daily_money"), weight=5.0)

        score = readiness_score + trend_score + move_score + rs_score + setup_score + spot_liquidity_score + futures_liquidity_score
        return round(max(0.0, min(score, 100.0)), 2)

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
            ranked.append(item)

        ranked.sort(key=lambda item: (
            item.get("candidate_score", 0.0),
            item.get("spot_ready_time", item.get("ready_time")) is not None,
            item.get("spot_ready_time", item.get("ready_time")) or "99:99",
            item.get("relative_strength", 0.0),
            item.get("average_daily_money", 0.0),
        ), reverse=True)

        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank
        return ranked[:int(limit)] if limit is not None else ranked
