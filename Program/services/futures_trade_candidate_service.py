"""SPOT-first candidate ranking for Trader_7_12 Pro.

The service selects BASE ASSETS. Futures are reference mapping only and never
participate in eligibility, direction, Relative Strength, setup or ranking.
"""

from services.market_trading_universe_service import MarketTradingUniverseService


class FuturesTradeCandidateService:
    VERSION = "2.1"
    MONEY_LEADER_SHORTLIST = 20
    TARGET_SPOT_GROUPS = MarketTradingUniverseService.TARGET_GROUPS

    def __init__(self, confirmation_service=None):
        # Kept for backward-compatible construction; intentionally unused.
        self.confirmation_service = None
        self.last_rank_diagnostics = {}

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
    def _spot_group(cls, item):
        return MarketTradingUniverseService.spot_group(item) if isinstance(item, dict) else None

    @classmethod
    def calculate_score(cls, radar, confirmation=None):
        """Calculate opportunity score from SPOT data only."""
        direction = cls._direction(radar)
        activity = max(0.0, cls._float(
            radar.get("spot_session_activity_ratio", radar.get("spot_money_ratio"))
        ))
        activity_score = min(activity / 3.0, 1.0) * 100.0

        money_per_minute = max(0.0, cls._float(radar.get("spot_money_per_minute")))
        money_volume = max(0.0, cls._float(radar.get("spot_money_volume")))
        money_presence_bonus = min(money_per_minute / 50_000_000.0 * 5.0, 5.0)
        absolute_money_bonus = min(money_volume / 1_000_000_000.0 * 5.0, 5.0)

        rs = cls._float(radar.get("relative_strength"))
        directional_rs = rs if direction == "LONG" else -rs if direction == "SHORT" else 0.0
        rs_bonus = max(-10.0, min(10.0, directional_rs * 20.0))

        change = cls._float(radar.get("change_percent"))
        directional_change = change if direction == "LONG" else -change if direction == "SHORT" else 0.0
        movement_bonus = max(-5.0, min(5.0, directional_change * 5.0))

        setup_quality = max(0.0, min(100.0, cls._float(radar.get("setup_quality_score"))))
        setup_bonus = min(setup_quality * 0.03, 3.0)

        score = (
            activity_score * 0.60
            + money_presence_bonus
            + absolute_money_bonus
            + rs_bonus
            + movement_bonus
            + setup_bonus
        )
        return round(max(0.0, min(score, 100.0)), 2)

    @classmethod
    def rejection_reason(cls, radar):
        """Return the first deterministic reason a SPOT radar item is not eligible."""
        if not isinstance(radar, dict):
            return "INVALID_RADAR"

        direction = cls._direction(radar)
        if direction not in {"LONG", "SHORT"}:
            return "NO_DIRECTION"
        if bool(radar.get("moex_event_risk")):
            return "EVENT_RISK"

        rs_status = str(radar.get("relative_strength_status") or "").upper()
        if rs_status not in {"OK", "AVAILABLE"}:
            return "RS_UNAVAILABLE"
        rs = cls._float(radar.get("relative_strength"))
        if direction == "LONG" and rs <= 0.0:
            return "RS_AGAINST_LONG"
        if direction == "SHORT" and rs >= 0.0:
            return "RS_AGAINST_SHORT"

        if cls._spot_group(radar) not in cls.TARGET_SPOT_GROUPS:
            return "WRONG_SPOT_GROUP"

        setup_phase = str(radar.get("setup_phase") or "UNKNOWN").upper()
        if setup_phase in {"NO_SESSION_CANDLES", "SETUP_ERROR"} or radar.get("setup_error"):
            return "SETUP_DATA_ERROR"

        setup_state = str(radar.get("setup_state") or "WAIT").upper()
        if setup_state not in {"WAIT", "WATCH", "READY", "CONFIRMED"}:
            return "INVALID_SETUP_STATE"

        return None

    @classmethod
    def build_candidate(cls, radar, confirmation=None):
        if cls.rejection_reason(radar) is not None:
            return None

        direction = cls._direction(radar)
        rs_status = str(radar.get("relative_strength_status") or "").upper()
        rs = cls._float(radar.get("relative_strength"))
        setup_phase = str(radar.get("setup_phase") or "UNKNOWN").upper()
        setup_state = str(radar.get("setup_state") or "WAIT").upper()

        return {
            "version": cls.VERSION,
            "status": "WATCHLIST",
            "direction": direction,
            "spot_group": cls._spot_group(radar),
            "market_group": cls._spot_group(radar),
            "futures_ticker": radar.get("futures_ticker"),
            "futures_class_code": radar.get("futures_class_code"),
            "futures_expiry": radar.get("futures_expiry"),
            "futures_days_to_expiry": int(cls._float(radar.get("days_to_expiry"))),
            "spot_ticker": radar.get("spot_ticker"),
            "spot_class_code": radar.get("spot_class_code"),
            "spot_name": radar.get("spot_name", ""),
            "spot_type": radar.get("spot_type", ""),
            "spot_price": cls._float(radar.get("spot_price", radar.get("last_close"))),
            "spot_money_volume": cls._float(radar.get("spot_money_volume")),
            "spot_average_daily_money": cls._float(radar.get("spot_average_daily_money", radar.get("average_daily_money"))),
            "spot_money_ratio": cls._float(radar.get("spot_money_ratio")),
            "spot_session_activity_ratio": cls._float(radar.get("spot_session_activity_ratio")),
            "spot_money_per_minute": cls._float(radar.get("spot_money_per_minute")),
            "session_elapsed_minutes": int(cls._float(radar.get("session_elapsed_minutes"))),
            "session_expected_minutes": int(cls._float(radar.get("session_expected_minutes"))),
            "spot_change_percent": cls._float(radar.get("change_percent")),
            "moex_event_risk": bool(radar.get("moex_event_risk")),
            "moex_da_trigger_inferred": bool(radar.get("moex_da_trigger_inferred")),
            "moex_da_trigger_percent": cls._float(radar.get("moex_da_trigger_percent"), 20.0),
            "moex_da_window_minutes": int(cls._float(radar.get("moex_da_window_minutes"), 10)),
            "moex_weekend_band_percent": cls._float(radar.get("moex_weekend_band_percent"), 3.0),
            "moex_weekend_band_near": bool(radar.get("moex_weekend_band_near")),
            "moex_weekend_band_hit": bool(radar.get("moex_weekend_band_hit")),
            "moex_max_abs_move_percent": cls._float(radar.get("moex_max_abs_move_percent")),
            "moex_price_stability_state": radar.get("moex_price_stability_state", "NORMAL"),
            "moex_price_stability_reason": radar.get("moex_price_stability_reason", ""),
            "moex_candles_loaded": int(cls._float(radar.get("moex_candles_loaded"))),
            "moex_data_status": radar.get("moex_data_status", "NO_DATA"),
            "trend_state": radar.get("trend_state", "UNKNOWN"),
            "trend_days": int(cls._float(radar.get("trend_days"))),
            "radar_score": round(cls._float(radar.get("radar_score")), 2),
            "relative_strength": rs,
            "relative_strength_score": cls._float(radar.get("relative_strength_score")),
            "relative_strength_signal": radar.get("relative_strength_signal", "UNAVAILABLE"),
            "relative_strength_status": rs_status,
            "relative_strength_benchmark": radar.get("relative_strength_benchmark", "UNAVAILABLE"),
            "setup": radar.get("setup", "NONE"),
            "setup_direction": radar.get("setup_direction", direction),
            "setup_state": setup_state,
            "setup_phase": setup_phase,
            "setup_quality_score": cls._float(radar.get("setup_quality_score")),
            "impulse_percent": cls._float(radar.get("impulse_percent")),
            "retracement_percent": cls._float(radar.get("retracement_percent")),
            "retracement_ratio": cls._float(radar.get("retracement_ratio")),
            "consolidation_candles": int(cls._float(radar.get("consolidation_candles"))),
            "entry_trigger": cls._float(radar.get("entry_trigger")),
            "previous_high": cls._float(radar.get("previous_high")),
            "previous_low": cls._float(radar.get("previous_low")),
            "impulse_high": cls._float(radar.get("impulse_high")),
            "impulse_low": cls._float(radar.get("impulse_low")),
            "h1_support": cls._float(radar.get("h1_support")),
            "h1_resistance": cls._float(radar.get("h1_resistance")),
            "h1_nearest_level": cls._float(radar.get("h1_nearest_level")),
            "h1_nearest_level_type": radar.get("h1_nearest_level_type", "NONE"),
            "h1_level_distance_percent": cls._float(radar.get("h1_level_distance_percent")),
            "h1_level_context": radar.get("h1_level_context", "UNAVAILABLE"),
            "candidate_score": cls.calculate_score(radar),
        }

    @classmethod
    def _select_money_leader_radars(cls, radar_results):
        candidates = [
            item for item in radar_results
            if isinstance(item, dict) and cls._spot_group(item) in cls.TARGET_SPOT_GROUPS
        ]
        candidates.sort(
            key=lambda item: (
                cls._float(item.get("spot_session_activity_ratio", item.get("spot_money_ratio"))),
                cls._float(item.get("spot_money_per_minute")),
                cls._float(item.get("spot_money_volume")),
                abs(cls._float(item.get("relative_strength"))),
                cls._float(item.get("setup_quality_score")),
                str(item.get("spot_ticker") or ""),
            ),
            reverse=True,
        )
        return candidates[:cls.MONEY_LEADER_SHORTLIST]

    @classmethod
    def _directional_rs_tiebreak(cls, item):
        direction = str(item.get("direction") or "").upper()
        rs = cls._float(item.get("relative_strength"))
        return rs if direction == "LONG" else -rs if direction == "SHORT" else 0.0

    def rank(self, radar_results, confirmations=None, limit=3):
        self.last_rank_diagnostics = {
            "input": 0,
            "money_leaders": 0,
            "accepted": 0,
            "rejected": 0,
            "rejections": {},
        }
        if not isinstance(radar_results, list):
            return []
        if limit is not None:
            limit = int(limit)
            if limit < 0:
                raise ValueError("limit must be >= 0")

        self.last_rank_diagnostics["input"] = len(radar_results)
        money_leaders = self._select_money_leader_radars(radar_results)
        self.last_rank_diagnostics["money_leaders"] = len(money_leaders)

        candidates = []
        for radar in money_leaders:
            reason = self.rejection_reason(radar)
            if reason is not None:
                self.last_rank_diagnostics["rejected"] += 1
                rejections = self.last_rank_diagnostics["rejections"]
                rejections[reason] = rejections.get(reason, 0) + 1
                continue
            candidate = self.build_candidate(radar)
            if candidate is not None:
                candidates.append(candidate)
                self.last_rank_diagnostics["accepted"] += 1

        candidates.sort(
            key=lambda item: (
                item["candidate_score"],
                item["spot_session_activity_ratio"],
                item["spot_money_per_minute"],
                item["spot_money_volume"],
                self._directional_rs_tiebreak(item),
                item["setup_quality_score"],
                item["spot_ticker"],
            ),
            reverse=True,
        )

        selected = []
        seen = set()
        for candidate in candidates:
            key = candidate.get("spot_ticker")
            if key in seen:
                continue
            seen.add(key)
            selected.append(candidate)
            if limit is not None and len(selected) >= limit:
                break

        for rank, candidate in enumerate(selected, start=1):
            candidate["rank"] = rank
        self.last_rank_diagnostics["selected"] = len(selected)
        return selected
