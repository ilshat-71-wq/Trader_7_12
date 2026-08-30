"""Full-market scanner wrapper: equities + direct macro fallback."""

from services.morning_trading_pipeline_service import MorningTradingPipelineService
from services.macro_market_radar_service import MacroMarketRadarService


class FullMarketPipelineService(MorningTradingPipelineService):
    """Keep canonical SPOT analysis and add explicit macro coverage."""

    VERSION = "1.1"

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
        # Preserve the canonical SPOT/equity path exactly as the base pipeline.
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

        # Direct macro candidates use the same lifecycle machinery, but their
        # price is explicitly the analysed futures proxy price.
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
            "macro_sources": sorted({str(x.get("macro_analysis_status") or "UNKNOWN") for x in macro}),
        }
        if selected:
            selected[0]["scan_diagnostics"] = dict(self._last_scan_diagnostics)
        return selected

    @staticmethod
    def print_results(results):
        print()
        print("=" * 150)
        print("TRADER_7_12 PRO - FULL MARKET: SPOT + OIL + GOLD + GAS + USDRUB")
        print("=" * 150)
        print()
        print(f"{'RANK':<6}{'ASSET':<12}{'SOURCE':<18}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<18}{'TRIGGER':>12}{'SCORE':>9}")
        print("-" * 150)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('spot_ticker', '-'): <12}"
                f"{item.get('analysis_source', '-'): <18}"
                f"{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}"
                f"{str(item.get('setup', '-')):<18}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
                f"{float(item.get('opportunity_score', item.get('candidate_score', 0)) or 0):>9.2f}"
            )
        if results:
            first = results[0]
            diagnostics = first.get("scan_diagnostics")
            print()
            print(f"SESSION: {first.get('market_session_label', first.get('market_session', '-'))}")
            print(f"TIME: {first.get('market_date', '-')} {first.get('market_time', '-')} MSK")
            if diagnostics:
                print(
                    "DIAGNOSTICS: "
                    f"SPOT={diagnostics.get('spot_candidates', 0)} "
                    f"MACRO={diagnostics.get('macro_candidates', 0)} "
                    f"TOTAL={diagnostics.get('candidates', 0)} "
                    f"SELECTED={diagnostics.get('selected', 0)} "
                    f"READY={diagnostics.get('ready', 0)} "
                    f"CONFIRMED={diagnostics.get('confirmed', 0)} "
                    f"WATCH={diagnostics.get('watch', 0)} "
                    f"WAIT={diagnostics.get('wait', 0)} "
                    f"MACRO_SOURCES={diagnostics.get('macro_sources', [])}"
                )
        else:
            print("NO WATCHLIST CANDIDATES")
        print()
        print("SPOT: canonical SPOT direction/setup/trigger/readiness; futures are mapping-only.")
        print("MACRO: explicit FUTURES_DIRECT coverage when usable SPOT data is unavailable.")
        print("MACRO INTRADAY_PROXY: used only when canonical daily radar cannot determine direction.")
        print("RS is not synthesized for macro direct candidates. Scanner is read-only; no orders, sizing or SL/TP.")
        print("=" * 150)
