"""Full-market read-only scanner: all TQBR stocks + direct macro futures.

Discovery is money-first: every canonical TQBR stock is screened for current
session money/pace, then only the most active stocks receive expensive
trend/RS/setup analysis. OIL/GOLD/GAS/FX are scanned through the explicit
FUTURES_DIRECT coverage layer because suitable SPOT data is not consistently
available for those markets.
"""

from services.morning_trading_pipeline_service import MorningTradingPipelineService
from services.macro_market_radar_service import MacroMarketRadarService
from services.broad_market_money_scanner_service import BroadMarketMoneyScannerService
from services.spot_universe_service import SpotUniverseService
from services.session_money_volume_service import SessionMoneyVolumeService


class FullMarketPipelineService(MorningTradingPipelineService):
    """Scan the broad market and return the best current opportunities."""

    VERSION = "1.2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        radar = self.radar_service
        api = getattr(radar, "api", None) or getattr(getattr(radar, "mapping_service", None), "api", None)
        # Broad-market discovery must be independent from optional
        # futures-radar attributes.  Always guarantee a real SPOT universe
        # and a real session-money service before constructing the scanner.
        session_money_service = getattr(radar, "session_money_service", None)
        if session_money_service is None:
            session_money_service = SessionMoneyVolumeService(
                history_service=getattr(radar, "history_service", None),
                session_service=self.session_service,
            )

        spot_universe_service = getattr(radar, "spot_universe_service", None)
        if spot_universe_service is None:
            spot_universe_service = SpotUniverseService(api=api)

        self.macro_radar = MacroMarketRadarService(
            api=api,
            radar_service=radar,
            session_service=self.session_service,
            session_money_service=session_money_service,
            setup_service=getattr(radar, "spot_setup_service", None),
        )

        self.broad_money_scanner = BroadMarketMoneyScannerService(
            spot_universe_service=spot_universe_service,
            session_money_service=session_money_service,
            session_service=self.session_service,
        )

    def scan(self, mappings=None, confirmations=None, limit=3):
        # Explicit mappings remain supported for tests/replay. Live production
        # discovery uses every canonical TQBR stock before deep analysis.
        if mappings is None:
            stock_money_ranked = self.broad_money_scanner.rank_current_money()
            deep_mappings = self.broad_money_scanner.top_for_deep_analysis()
        else:
            stock_money_ranked = list(mappings or [])
            deep_mappings = list(mappings or [])

        base = super().scan(
            mappings=deep_mappings,
            confirmations=confirmations,
            limit=None,
        )
        macro = self.macro_radar.scan(limit=None)

        money_by_ticker = {
            str(item.get("spot_ticker") or "").strip().upper(): item
            for item in stock_money_ranked
            if isinstance(item, dict)
        }
        for item in base:
            ticker = str(item.get("spot_ticker") or "").strip().upper()
            money = money_by_ticker.get(ticker, {})
            item["spot_universe"] = "ALL_TQBR_STOCKS"
            item["market_universe"] = "ALL_TQBR_STOCKS"
            item["market_group"] = "MOEX_STOCK"
            item["money_rank"] = money.get("money_rank")
            item["spot_session_money"] = money.get("spot_session_money", item.get("spot_money_volume", 0))
            item["spot_money_per_minute"] = money.get(
                "spot_money_per_minute",
                item.get("spot_money_per_minute", 0),
            )
            item["money_scan_status"] = money.get("money_scan_status", "DEEP")
            item["broad_stock_universe"] = True

        combined = list(base or []) + list(macro or [])
        for item in combined:
            item.setdefault("analysis_source", "SPOT")
            item.setdefault("spot_data_status", "AVAILABLE")
            item.setdefault("opportunity_score", item.get("candidate_score", 0))
            item.setdefault("session_rank_score", item.get("candidate_score", 0))
            item.setdefault("setup_score", item.get("setup_quality_score", 0))
            item.setdefault("setup_state", "WAIT")

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
                float(item.get("spot_session_money", item.get("spot_money_volume", 0)) or 0),
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
            "stock_universe_total": len(stock_money_ranked),
            "stock_money_screened": len(stock_money_ranked),
            "stock_deep_analyzed": len(base or []),
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
        print("=" * 170)
        print("TRADER_7_12 PRO - FULL MARKET: ALL TQBR STOCKS + OIL + GOLD + GAS + FX")
        print("=" * 170)
        print()
        print(f"{'RANK':<6}{'ASSET':<12}{'SOURCE':<18}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<18}{'TRIGGER':>12}{'MONEY RANK':>12}{'SCORE':>9}")
        print("-" * 170)
        for item in results:
            money_rank = item.get("money_rank", "-")
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('spot_ticker', '-'): <12}"
                f"{item.get('analysis_source', '-'): <18}"
                f"{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}"
                f"{str(item.get('setup', '-')):<18}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
                f"{str(money_rank):>12}"
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
                    f"ALL_TQBR={diagnostics.get('stock_universe_total', 0)} "
                    f"MONEY_SCREENED={diagnostics.get('stock_money_screened', 0)} "
                    f"DEEP={diagnostics.get('stock_deep_analyzed', 0)} "
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
        print("STOCKS: all canonical MOEX TQBR stocks are money-screened first; only the most active receive deep SPOT analysis.")
        print("MACRO: OIL/GOLD/GAS/FX are explicit FUTURES_DIRECT coverage when usable SPOT data is unavailable.")
        print("Futures are reference-only for equities and do not confirm SPOT signals. Macro futures are analysed directly and labelled as such.")
        print("RS is never synthesized. Scanner is read-only: no orders, sizing or SL/TP.")
        print("=" * 170)
