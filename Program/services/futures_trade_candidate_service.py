"""Spot-first candidate selection for Trader_7_12 Pro.

The scanner selects BASE ASSETS. Futures are only a mapped trading instrument
shown to the user; futures trades, futures price movement and futures
confirmation never determine eligibility, direction, RS or score.
"""

from services.market_trading_universe_service import MarketTradingUniverseService


class FuturesTradeCandidateService:
    VERSION = "1.3"
    MAX_DAYS_TO_EXPIRY = 3

    # Event-driven / abnormal price movement must never enter
    # the normal TOP-2/3 trading selection.
    EVENT_MAX_DAILY_TREND_PERCENT = 15.0

    # Do not discard strong current-day instruments before eligibility checks.
    # The preliminary/deep radar already limits the universe by current-session
    # money/activity. Candidate ranking must then see the whole deep shortlist
    # so RS, direction and setup quality can determine the final TOP-N.
    MONEY_LEADER_SHORTLIST = 20
    TARGET_SPOT_GROUPS = MarketTradingUniverseService.TARGET_GROUPS

    def __init__(self, confirmation_service=None):
        # Kept for constructor compatibility. Intentionally unused.
        self.confirmation_service = None

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
        if not isinstance(item, dict):
            return None
        return MarketTradingUniverseService.spot_group(item)

    @classmethod
    def calculate_score(cls, radar, confirmation=None):
        """Score only SPOT money/activity, direction, RS and setup context."""
        direction = cls._direction(radar)
        activity = max(0.0, cls._float(
            radar.get("spot_session_activity_ratio", radar.get("spot_money_ratio"))
        ))
        money_score = min(activity / 3.0, 1.0) * 100.0
        money_per_minute = max(0.0, cls._float(radar.get("spot_money_per_minute")))
        money_volume = max(0.0, cls._float(radar.get("spot_money_volume")))
        money_presence_bonus = min((money_per_minute / 50_000_000.0) * 5.0, 5.0)
        absolute_money_bonus = min((money_volume / 1_000_000_000.0) * 5.0, 5.0)

        rs = cls._float(radar.get("relative_strength"))
        directional_rs = rs if direction == "LONG" else -rs if direction == "SHORT" else 0.0
        rs_bonus = max(-10.0, min(10.0, directional_rs * 20.0))

        change = cls._float(radar.get("change_percent"))
        directional_change = change if direction == "LONG" else -change if direction == "SHORT" else 0.0
        movement_bonus = max(-5.0, min(5.0, directional_change * 5.0))

        setup_quality = max(0.0, min(100.0, cls._float(radar.get("setup_quality_score"))))
        setup_bonus = min(setup_quality * 0.03, 3.0)
        setup_state = str(radar.get("setup_state") or "WAIT").upper()
        if setup_state == "CONFIRMED":
            setup_bonus += 1.0
        elif setup_state == "WATCH":
            setup_bonus += 0.5

        score = money_score * 0.60 + money_presence_bonus + absolute_money_bonus + rs_bonus + movement_bonus + setup_bonus
        return round(max(0.0, min(score, 100.0)), 2)

    @classmethod
    def build_candidate(cls, radar, confirmation=None):
        if not isinstance(radar, dict):
            return None
        direction = cls._direction(radar)
        if direction not in {"LONG", "SHORT"}:
            return None

        # Hard exclusion for event-driven / abnormal SPOT movement.
        # Such instruments require a different trading scheme and must
        # never compete with normal continuation setups.
        change = abs(cls._float(radar.get("change_percent")))
        if change >= cls.EVENT_MAX_DAILY_TREND_PERCENT:
            return None

        # Direction must agree with the BASE ASSET's relative strength.
        # LONG requires SPOT to outperform the benchmark; SHORT requires
        # SPOT to underperform it. Futures never participate in this rule.
        rs = cls._float(radar.get("relative_strength"))
        if direction == "LONG" and rs <= 0.0:
            return None
        if direction == "SHORT" and rs >= 0.0:
            return None

        spot_group = cls._spot_group(radar)
        if spot_group not in cls.TARGET_SPOT_GROUPS:
            return None

        # Futures are not part of SPOT candidate eligibility.
        # Expiry, futures price, futures volume and futures confirmation
        # must never remove a BASE ASSET from the radar.

        setup_phase = str(radar.get("setup_phase") or "UNKNOWN").upper()
        setup_error = radar.get("setup_error")

        # Final TOP selection requires valid SPOT M5 data.
        # Missing/failed M5 data must never be promoted by a high
        # activity/pace score alone.
        if setup_phase in {"NO_SESSION_CANDLES", "SETUP_ERROR"} or setup_error:
            return None

        score = cls.calculate_score(radar)
        return {
            "version": cls.VERSION,
            "status": "READY",
            "direction": direction,
            "spot_group": spot_group,
            "market_group": spot_group,
            # Mapping only: no futures market data is used for selection.
            "futures_ticker": radar.get("futures_ticker"),
            "futures_class_code": radar.get("futures_class_code"),
            "futures_expiry": radar.get("futures_expiry"),
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
            "relative_strength": rs,
            "relative_strength_score": cls._float(radar.get("relative_strength_score")),
            "relative_strength_signal": radar.get("relative_strength_signal", "UNAVAILABLE"),
            "relative_strength_status": radar.get("relative_strength_status", "NO_DATA"),
            "relative_strength_benchmark": radar.get("relative_strength_benchmark", "UNAVAILABLE"),
            "confirmation_score": 0.0,
            "money_volume": 0.0,
            "trade_count": 0,
            "price_change_percent": 0.0,
            "setup": radar.get("setup", "NONE"),
            "setup_direction": radar.get("setup_direction", direction),
            "setup_state": radar.get("setup_state", "WAIT"),
            "setup_phase": setup_phase,
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
        candidates = [
            item for item in radar_results
            if isinstance(item, dict) and cls._spot_group(item) in cls.TARGET_SPOT_GROUPS
        ]
        candidates.sort(key=lambda item: (
            cls._float(item.get("spot_session_activity_ratio", item.get("spot_money_ratio"))),
            cls._float(item.get("spot_money_per_minute")),
            cls._float(item.get("spot_money_volume")),
            cls._float(item.get("relative_strength")),
            cls._float(item.get("setup_quality_score")),
            str(item.get("spot_ticker") or ""),
        ), reverse=True)
        return candidates[:cls.MONEY_LEADER_SHORTLIST]

    def rank(self, radar_results, confirmations=None, limit=3):
        if not isinstance(radar_results, list):
            return []
        limit = 3 if limit is None else int(limit)
        if limit < 0:
            raise ValueError("limit must be >= 0")

        candidates = []
        for radar in self._select_money_leader_radars(radar_results):
            candidate = self.build_candidate(radar)
            if candidate is not None:
                candidates.append(candidate)

        # One result per BASE ASSET. No futures liquidity/turnover is consulted.
        candidates.sort(key=lambda item: (
            item["spot_session_activity_ratio"],
            item["spot_money_per_minute"],
            item["spot_money_volume"],
            item["candidate_score"],
            item["relative_strength"],
            item["setup_quality_score"],
            item["spot_ticker"],
        ), reverse=True)

        seen = set()
        selected = []
        for candidate in candidates:
            key = candidate.get("spot_ticker")
            if key in seen:
                continue
            seen.add(key)
            selected.append(candidate)
            if len(selected) >= limit:
                break

        for rank, candidate in enumerate(selected, start=1):
            candidate["rank"] = rank
        return selected
