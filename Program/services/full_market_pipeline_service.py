"""Full-market scanner wrapper: equities + direct macro fallback."""

from services.morning_trading_pipeline_service import MorningTradingPipelineService
from services.macro_market_radar_service import MacroMarketRadarService


class FullMarketPipelineService(MorningTradingPipelineService):
    """Keep the canonical SPOT pipeline and add explicit macro coverage."""

    VERSION = "1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        radar = self.radar_service
        self.macro_radar = MacroMarketRadarService(
            api=getattr(radar, "api", None) or getattr(getattr(radar, "mapping_service", None), "api", None),
            radar_service=radar,
            session_service=self.session_service,
            session_money_service=getattr(radar, "session_money_service", None),
            setup_service=getattr(radar, "spot_setup_service", None),
        )

    def scan(self, mappings=None, confirmations=None, limit=3):
        # Preserve the existing equity/SPOT path exactly as the canonical base.
        base = super().scan(mappings=mappings, confirmations=confirmations, limit=None)
        macro = self.macro_radar.scan(limit=None)

        combined = list(base or []) + list(macro or [])
        for item in combined:
            item.setdefault("analysis_source", "SPOT")
            item.setdefault("spot_data_status", "AVAILABLE")
            item.setdefault("opportunity_score", item.get("candidate_score", 0))
            item.setdefault("session_rank_score", item.get("candidate_score", 0))
            item.setdefault("setup_score", item.get("setup_quality_score", 0))
            item.setdefault("setup_state", "WAIT")

        # Apply the same canonical two-observation lifecycle to direct macro
        # candidates. Their "spot_price" is explicitly the futures proxy price.
        for item in macro:
            self._advance_signal_state(item)
            item["market_session"] = self.session_service.get_session()
            item["session_rank_score"] = self._session_rank_score(item, item["market_session"])
            item["opportunity_score"] = item["session_rank_score"]
            item["setup_score"] = self._setup_score(item)
            item["selection_role"] = "TOP_WATCHLIST"

        combined.sort(
            key=lambda item: (
                self._signal_priority(item.get("signal_state")),
                float(item.get("opportunity_score", item.get("candidate_score", 0)) or 0),
                float(item.get("candidate_score", 0) or 0),
                float(item.get("setup_score", 0) or 0),
                float(item.get("spot_session_activity_ratio", 0) or 0),
                float(item.get("spot_money_per_minute", 0) or 0),
                str(item.get("spot_ticker") or ""),
            ),
            reverse=True,
        )

        selected = combined[: max(0, int(limit or 0))]
        for rank, item in enumerate(selected, start=1):
            item["rank"] = rank
            item["pipeline_version"] = self.VERSION

        self._last_scan_diagnostics = {
            "session": self.session_service.get_session(),
            "radar_results": len(base or []) + len(macro or []),
            "spot_candidates": len(base or []),
            "macro_candidates": len(macro or []),
            "candidates": len(combined),
            "selected": len(selected),
            "ready": sum(1 for x in combined if x.get("signal_state") == "READY"),
            "confirmed": sum(1 for x in combined if x.get("signal_state") == "CONFIRMED"),
            "watch": sum(1 for x in combined if str(x.get("setup_state") or "").upper() == "WATCH"),
            "wait": sum(1 for x in combined if str(x.get("setup_state") or "").upper() == "WAIT"),
        }
        if selected:
            selected[0]["scan_diagnostics"] = dict(self._last_scan_diagnostics)
        return selected
