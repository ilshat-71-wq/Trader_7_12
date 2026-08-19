"""
Trader_7_12 Pro

Futures Trade Candidate Service.

Stage 5 of the Spot-first architecture.

The scanner universe is the current IMOEX equity basket plus the configured
macro markets OIL/GOLD/GAS/USDRUB. The trading instrument is the mapped
futures contract. The service does not place orders and does not invent the
user's exact entry.
"""

from datetime import date

from services.market_trading_universe_service import MarketTradingUniverseService


class FuturesTradeCandidateService:
    """Build and rank final scanner candidates."""

    VERSION = "1.0"
    MAX_DAYS_TO_EXPIRY = 3
    MONEY_LEADER_SHORTLIST = 5
    TARGET_SPOT_GROUPS = MarketTradingUniverseService.TARGET_GROUPS

    def __init__(self, confirmation_service=None):
        self.confirmation_service = confirmation_service

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _expiry_is_eligible(cls, expiry):
        if not expiry:
            return True
        try:
            expiry_date = date.fromisoformat(str(expiry)[:10])
        except ValueError:
            return False
        return (expiry_date - date.today()).days > cls.MAX_DAYS_TO_EXPIRY

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
        """
        Candidate score answers one question:

        Where are money and unusual activity appearing TODAY,
        and is there enough directional/movement confirmation to watch it?

        Setup is deliberately NOT a gate and has only a small quality bonus.
        The scanner finds WHERE to look; the user decides WHEN to enter.
        """
        direction = cls._direction(radar)

        activity = max(
            0.0,
            cls._float(
                radar.get(
                    "spot_session_activity_ratio",
                    radar.get("spot_money_ratio"),
                )
            ),
        )

        # Convert activity anomaly into a bounded 0..100 component.
        # 1.0x = normal, 2.0x = strong, 3.0x+ = exceptional.
        money_score = min(activity / 3.0, 1.0) * 100.0

        money_per_minute = max(
            0.0,
            cls._float(radar.get("spot_money_per_minute")),
        )
        money_volume = max(
            0.0,
            cls._float(radar.get("spot_money_volume")),
        )

        # Activity remains the dominant factor. Absolute money only
        # breaks ties between otherwise similar activity leaders.
        money_presence_bonus = min(
            (money_per_minute / 50_000_000.0) * 5.0,
            5.0,
        )
        absolute_money_bonus = min(
            (money_volume / 1_000_000_000.0) * 5.0,
            5.0,
        )

        futures_score = max(
            0.0,
            min(100.0, cls._float(confirmation.get("score"))),
        )

        rs = cls._float(radar.get("relative_strength"))
        directional_rs = rs if direction == "LONG" else -rs if direction == "SHORT" else 0.0
        rs_bonus = max(-10.0, min(10.0, directional_rs * 20.0))

        futures_change = cls._float(confirmation.get("price_change_percent"))
        directional_change = (
            futures_change
            if direction == "LONG"
            else -futures_change
            if direction == "SHORT"
            else 0.0
        )
        movement_bonus = max(-5.0, min(5.0, directional_change * 5.0))

        setup_state = str(radar.get("setup_state") or "WAIT").upper()
        setup_quality = max(
            0.0,
            min(100.0, cls._float(radar.get("setup_quality_score"))),
        )

        # Setup is context, not an entry signal and not a candidate gate.
        setup_bonus = min(setup_quality * 0.03, 3.0)
        if setup_state == "CONFIRMED":
            setup_bonus += 1.0
        elif setup_state == "WATCH":
            setup_bonus += 0.5

        score = (
            money_score * 0.60
            + futures_score * 0.15
            + money_presence_bonus
            + absolute_money_bonus
            + rs_bonus
            + movement_bonus
            + setup_bonus
        )

        return round(max(0.0, min(score, 100.0)), 2)

    @classmethod
    def build_candidate(cls, radar, confirmation):
        if not isinstance(radar, dict) or not isinstance(confirmation, dict):
            return None
        if not cls._expiry_is_eligible(radar.get("futures_expiry")):
            return None
        if str(confirmation.get("status", "")).upper() != "OK":
            return None
        direction = cls._direction(radar)
        confirmed_direction = str(confirmation.get("direction") or "NONE").upper()
        if direction not in {"LONG", "SHORT"} or confirmed_direction != direction:
            return None
        spot_group = cls._spot_group(radar)
        if spot_group is None:
            return None
        score = cls.calculate_score(radar, confirmation)
        return {
            "version": cls.VERSION,
            "status": "READY",
            "direction": direction,
            "spot_group": spot_group,
            "market_group": spot_group,
            "futures_ticker": radar.get("futures_ticker"),
            "futures_class_code": radar.get("futures_class_code"),
            "futures_expiry": radar.get("futures_expiry"),
            "futures_price": cls._float(confirmation.get("last_price")),
            "spot_ticker": radar.get("spot_ticker"),
            "spot_class_code": radar.get("spot_class_code"),
            "spot_name": radar.get("spot_name", ""),
            "spot_type": radar.get("spot_type", ""),
            "spot_price": cls._float(radar.get("spot_price", radar.get("last_close"))),
            "spot_money_volume": cls._float(radar.get("spot_money_volume")),
            "spot_average_daily_money": cls._float(radar.get("average_daily_money")),
            "spot_money_ratio": cls._float(radar.get("spot_money_ratio")),
            "spot_session_activity_ratio": cls._float(radar.get("spot_session_activity_ratio")),
            "spot_money_per_minute": cls._float(radar.get("spot_money_per_minute")),
            "session_elapsed_minutes": int(cls._float(radar.get("session_elapsed_minutes"))),
            "session_expected_minutes": int(cls._float(radar.get("session_expected_minutes"))),
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
            "setup_phase": radar.get("setup_phase", "UNKNOWN"),
            "setup_quality_score": cls._float(radar.get("setup_quality_score")),
            "impulse_percent": cls._float(radar.get("impulse_percent")),
            "retracement_percent": cls._float(radar.get("retracement_percent")),
            "retracement_ratio": cls._float(radar.get("retracement_ratio")),
            "consolidation_candles": int(cls._float(radar.get("consolidation_candles"))),
            "entry_trigger": cls._float(radar.get("entry_trigger")),
            "previous_high": cls._float(radar.get("previous_high")),
            "previous_low": cls._float(radar.get("previous_low")),
            "candidate_score": score,
        }

    @classmethod
    def _select_money_leader_radars(cls, radar_results):
        """Keep the best money/activity leaders across all configured groups."""
        candidates = []
        for radar in radar_results:
            if not isinstance(radar, dict):
                continue
            if cls._spot_group(radar) in cls.TARGET_SPOT_GROUPS:
                candidates.append(radar)

        candidates.sort(key=lambda item: (
            cls._float(item.get("spot_session_activity_ratio", item.get("spot_money_ratio"))),
            cls._float(item.get("spot_money_volume")),
            cls._float(item.get("setup_quality_score")),
            cls._float(item.get("spot_money_ratio")),
            cls._float(item.get("radar_score")),
            cls._float(item.get("relative_strength")),
            str(item.get("spot_ticker") or ""),
        ), reverse=True)
        return candidates[: cls.MONEY_LEADER_SHORTLIST]

    @classmethod
    def _select_most_liquid_per_spot(cls, candidates):
        """One underlying gets one final contract: most liquid of the nearest two."""
        grouped = {}
        for candidate in candidates:
            spot_ticker = str(candidate.get("spot_ticker") or "").strip().upper()
            if spot_ticker:
                grouped.setdefault(spot_ticker, []).append(candidate)

        selected = []
        for spot_candidates in grouped.values():
            spot_candidates.sort(key=lambda item: (
                item["money_volume"],
                item["trade_count"],
                item["confirmation_score"],
                item["candidate_score"],
                str(item.get("futures_expiry") or "9999-12-31"),
                str(item.get("futures_ticker") or ""),
            ), reverse=True)
            selected.append(spot_candidates[0])
        return selected

    @classmethod
    def _spot_group(cls, item):
        if not isinstance(item, dict):
            return None
        return MarketTradingUniverseService.spot_group(item)

    def rank(self, radar_results, confirmations=None, limit=3):
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
        radar_results = self._select_money_leader_radars(radar_results)
        candidates = []

        for radar in radar_results:
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

        candidates = self._select_most_liquid_per_spot(candidates)
        # Final ranking: money/activity first.
        # Setup is deliberately last and never determines eligibility.
        candidates.sort(key=lambda item: (
            item["spot_session_activity_ratio"],
            item["spot_money_per_minute"],
            item["spot_money_volume"],
            item["candidate_score"],
            item["relative_strength"],
            item["confirmation_score"],
            item["money_volume"],
            item["trade_count"],
            item["setup_quality_score"],
            item["futures_ticker"],
        ), reverse=True)

        for rank, candidate in enumerate(candidates, start=1):
            candidate["rank"] = rank
        return candidates[:limit]
