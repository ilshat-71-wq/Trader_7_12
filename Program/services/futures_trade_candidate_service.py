"""
Trader_7_12 Pro

Futures Trade Candidate Service.

Stage 5 of the Spot-first architecture.

Purpose:
- combine SPOT Morning Radar with futures confirmation;
- reject blocked futures confirmations;
- calculate one comparable trade-candidate score;
- return only the best 2-3 candidates when requested.

The service does not place orders and does not invent a direction.
The direction always comes from the SPOT radar and must be confirmed by
futures.
"""


class FuturesTradeCandidateService:
    """Build and rank final morning scanner candidates."""

    VERSION = "0.3"

    def __init__(self, confirmation_service=None):
        self.confirmation_service = confirmation_service

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _direction(radar):
        direction = str(radar.get("direction") or "").upper()
        if direction in {"LONG", "SHORT"}:
            return direction

        signal = str(radar.get("signal") or "").upper()
        if "LONG" in signal:
            return "LONG"
        if "SHORT" in signal:
            return "SHORT"
        return "NONE"

    @classmethod
    def calculate_score(cls, radar, confirmation):
        """Calculate a deterministic 0-100 candidate score."""
        radar_score = max(0.0, min(100.0, cls._float(radar.get("radar_score"))))
        confirmation_score = max(
            0.0,
            min(100.0, cls._float(confirmation.get("score")))
        )

        direction = cls._direction(radar)
        rs = cls._float(radar.get("relative_strength"))

        # Directional relative-strength adjustment:
        # LONG  -> positive RS is favorable
        # SHORT -> negative RS is favorable
        directional_rs = rs if direction == "LONG" else -rs

        if directional_rs > 0:
            rs_bonus = min(directional_rs * 20.0, 10.0)
        elif directional_rs < 0:
            rs_bonus = max(directional_rs * 20.0, -10.0)
        else:
            rs_bonus = 0.0

        futures_change = cls._float(confirmation.get("price_change_percent"))
        directional_change = (
            futures_change
            if direction == "LONG"
            else -futures_change
            if direction == "SHORT"
            else 0.0
        )

        if directional_change > 0:
            futures_change_bonus = min(directional_change * 5.0, 5.0)
        elif directional_change < 0:
            futures_change_bonus = max(directional_change * 5.0, -5.0)
        else:
            futures_change_bonus = 0.0

        money_volume = cls._float(
            confirmation.get("money_volume", radar.get("spot_money_volume"))
        )
        liquidity_bonus = 0.0
        if money_volume >= 100_000_000:
            liquidity_bonus = 10.0
        elif money_volume >= 10_000_000:
            liquidity_bonus = 6.0
        elif money_volume >= 1_000_000:
            liquidity_bonus = 3.0

        score = (
            radar_score * 0.60
            + confirmation_score * 0.30
            + rs_bonus
            + futures_change_bonus
            + liquidity_bonus
        )
        return round(min(score, 100.0), 2)

    @classmethod
    def build_candidate(cls, radar, confirmation):
        """Return a candidate or None when the confirmation blocks it."""
        if not isinstance(radar, dict) or not isinstance(confirmation, dict):
            return None

        if str(confirmation.get("status", "")).upper() != "OK":
            return None

        direction = cls._direction(radar)
        confirmed_direction = str(
            confirmation.get("direction") or "NONE"
        ).upper()

        if direction not in {"LONG", "SHORT"}:
            return None
        if confirmed_direction != direction:
            return None

        score = cls.calculate_score(radar, confirmation)

        return {
            "version": cls.VERSION,
            "status": "READY",
            "direction": direction,
            "futures_ticker": radar.get("futures_ticker"),
            "futures_class_code": radar.get("futures_class_code"),
            "futures_expiry": radar.get("futures_expiry"),
            "futures_price": cls._float(confirmation.get("last_price")),
            "spot_ticker": radar.get("spot_ticker"),
            "spot_class_code": radar.get("spot_class_code"),
            "spot_price": cls._float(radar.get("spot_price", radar.get("last_close"))),
            "spot_money_volume": cls._float(radar.get("spot_money_volume", radar.get("average_daily_money"))),
            "spot_average_daily_money": cls._float(radar.get("average_daily_money")),
            "spot_change_percent": cls._float(radar.get("change_percent")),
            "trend_state": radar.get("trend_state", "UNKNOWN"),
            "trend_days": int(cls._float(radar.get("trend_days"))),
            "radar_score": round(cls._float(radar.get("radar_score")), 2),
            "relative_strength": cls._float(radar.get("relative_strength")),
            "relative_strength_score": cls._float(radar.get("relative_strength_score")),
            "relative_strength_signal": radar.get("relative_strength_signal", "UNAVAILABLE"),
            "relative_strength_status": radar.get("relative_strength_status", "NO_DATA"),
            "relative_strength_benchmark": radar.get("relative_strength_benchmark", "UNAVAILABLE"),
            "confirmation_score": cls._float(confirmation.get("score")),
            "money_volume": cls._float(confirmation.get("money_volume")),
            "trade_count": int(cls._float(confirmation.get("trade_count"))),
            "price_change_percent": cls._float(confirmation.get("price_change_percent")),
            "setup": radar.get("setup", "NONE"),
            "setup_direction": radar.get("setup_direction", direction),
            "setup_state": radar.get("setup_state", "WAIT"),
            "entry_trigger": cls._float(radar.get("entry_trigger")),
            "previous_high": cls._float(radar.get("previous_high")),
            "previous_low": cls._float(radar.get("previous_low")),
            "candidate_score": score,
        }

    def rank(self, radar_results, confirmations=None, limit=3):
        """Build candidates and return the strongest ones first."""
        if not isinstance(radar_results, list):
            return []

        if limit is None:
            limit = 3
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise TypeError("limit must be an integer")
        if limit < 0:
            raise ValueError("limit must be >= 0")

        confirmation_map = confirmations or {}

        # Cheap SPOT-first prefilter before expensive futures confirmation.
        radar_results = sorted(
            radar_results,
            key=lambda item: self._float(item.get("radar_score")),
            reverse=True,
        )[:15]

        candidates = []
        for radar in radar_results:
            if not isinstance(radar, dict):
                continue

            ticker = str(radar.get("futures_ticker") or "").strip().upper()
            confirmation = confirmation_map.get(ticker)

            if confirmation is None and self.confirmation_service is not None:
                confirmation = self.confirmation_service.analyze(
                    ticker,
                    radar.get("futures_class_code"),
                    self._direction(radar),
                )

            candidate = self.build_candidate(radar, confirmation)
            if candidate is not None:
                candidates.append(candidate)

        # Deterministic ranking: quality first, then liquidity and stability.
        candidates.sort(
            key=lambda item: (
                item["candidate_score"],
                item["confirmation_score"],
                item["radar_score"],
                item["money_volume"],
                item["spot_average_daily_money"],
                item["relative_strength"],
                item["trade_count"],
                item["futures_ticker"],
            ),
            reverse=True,
        )

        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank

        return candidates[:limit]
