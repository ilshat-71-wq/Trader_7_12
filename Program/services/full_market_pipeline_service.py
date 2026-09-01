"""Full-market read-only scanner: all TQBR stocks + separate macro futures watch.

Discovery is money-first: every canonical TQBR stock is screened for current
session money/pace, then only the most active stocks receive expensive trend/RS/setup
analysis. OIL/GOLD/GAS/FX remain a separate FUTURES_DIRECT watch layer and are never
returned as equity trade-radar candidates.
"""

from services.morning_trading_pipeline_service import MorningTradingPipelineService
from services.macro_market_radar_service import MacroMarketRadarService
from services.broad_market_money_scanner_service import BroadMarketMoneyScannerService
from services.spot_universe_service import SpotUniverseService
from services.session_money_volume_service import SessionMoneyVolumeService


class FullMarketPipelineService(MorningTradingPipelineService):
    """Scan the broad market while keeping SPOT trade radar separate from macro watch."""

    VERSION = "1.5"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        radar = self.radar_service
        api = getattr(radar, "api", None) or getattr(getattr(radar, "mapping_service", None), "api", None)
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
        if mappings is None:
            stock_money_ranked = self.broad_money_scanner.rank_current_money()
            deep_mappings = self.broad_money_scanner.top_for_deep_analysis()
        else:
            stock_money_ranked = list(mappings or [])
            deep_mappings = list(mappings or [])

        # Equity trade radar: SPOT only.
        base = super().scan(
            mappings=deep_mappings,
            confirmations=confirmations,
            limit=None,
        )

        # Macro is deliberately a separate watch layer. It is never merged into
        # the equity candidate ranking and therefore can never become #1 simply
        # because a futures proxy score is numerically larger.
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
            item["analysis_source"] = "SPOT"
            item["money_rank"] = money.get("money_rank")
            item["spot_session_money"] = money.get("spot_session_money", item.get("spot_money_volume", 0))
            item["spot_money_per_minute"] = money.get("spot_money_per_minute", item.get("spot_money_per_minute", 0))
            item["money_scan_status"] = money.get("money_scan_status", "DEEP")
            item["broad_stock_universe"] = True
            item["selection_role"] = "SPOT_TRADE_RADAR"

        for item in base:
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
            item["selection_role"] = "MACRO_WATCH"
            item["signal_state"] = "WAIT"
            item["futures_selection_reason"] = "MACRO_DIRECT_WATCH_ONLY"

        base.sort(
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

        selected = base[: max(0, int(limit or 0))]
        for rank, item in enumerate(selected, start=1):
            item["rank"] = rank
            item["pipeline_version"] = self.VERSION

        active_leaders = []
        for row in stock_money_ranked[:10]:
            active_leaders.append({
                "rank": row.get("money_rank"),
                "spot_ticker": row.get("spot_ticker"),
                "spot_session_money": row.get("spot_session_money", 0),
                "spot_money_per_minute": row.get("spot_money_per_minute", 0),
                "money_scan_status": row.get("money_scan_status", "ERROR"),
            })

        macro_watch = []
        for rank, item in enumerate(macro[:10], start=1):
            macro_watch.append({
                "rank": rank,
                "ticker": item.get("spot_ticker") or item.get("ticker") or "",
                "direction": item.get("direction"),
                "score": item.get("opportunity_score", 0),
                "setup": item.get("setup"),
                "session_money": item.get("spot_money_volume", item.get("macro_session_money", 0)),
                "money_per_minute": item.get("spot_money_per_minute", item.get("macro_money_per_minute", 0)),
                "signal_state": "WAIT",
                "analysis_source": "FUTURES_DIRECT",
            })

        rank_diagnostics = getattr(self.candidate_service, "last_rank_diagnostics", {}) or {}
        self._last_scan_diagnostics = {
            "session": self.session_service.get_session(),
            "stock_universe_total": len(stock_money_ranked),
            "stock_money_screened": len(stock_money_ranked),
            "stock_deep_analyzed": rank_diagnostics.get("input", len(base or [])),
            "spot_candidates": len(base or []),
            "macro_candidates": len(macro or []),
            "candidates": len(base or []),
            "selected": len(selected),
            "ready": sum(1 for x in base if x.get("signal_state") == "READY"),
            "confirmed": sum(1 for x in base if x.get("signal_state") == "CONFIRMED"),
            "watch": sum(1 for x in base if str(x.get("setup_state") or "").upper() == "WATCH"),
            "wait": sum(1 for x in base if str(x.get("setup_state") or "").upper() == "WAIT"),
            "money_leader_count": rank_diagnostics.get("money_leaders", 0),
            "candidate_accepted": rank_diagnostics.get("accepted", 0),
            "candidate_rejected": rank_diagnostics.get("rejected", 0),
            "candidate_rejections": dict(rank_diagnostics.get("rejections", {}) or {}),
            "macro_sources": sorted({str(x.get("macro_analysis_status") or "UNKNOWN") for x in macro}),
            "active_money_leaders": active_leaders,
            "macro_watch": macro_watch,
        }
        if selected:
            selected[0]["scan_diagnostics"] = dict(self._last_scan_diagnostics)
        return selected

    @staticmethod
    def print_results(results):
        print()
        print("=" * 170)
        print("TRADER_7_12 PRO - SPOT TRADE RADAR + SEPARATE MACRO WATCH")
        print("=" * 170)
        print()
        print(f"{'RANK':<6}{'SPOT':<12}{'SOURCE':<14}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<18}{'TRIGGER':>12}{'MONEY RANK':>12}{'SCORE':>9}")
        print("-" * 170)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('spot_ticker', '-'): <12}"
                f"{'SPOT / TQBR':<14}"
                f"{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}"
                f"{str(item.get('setup', '-')):<18}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
                f"{str(item.get('money_rank', '-')):>12}"
                f"{float(item.get('opportunity_score', item.get('candidate_score', 0)) or 0):>9.2f}"
            )
        diagnostics = results[0].get("scan_diagnostics") if results and isinstance(results[0], dict) else None
        if diagnostics:
            print()
            print("TOP ACTIVE MONEY — TQBR")
            for row in diagnostics.get("active_money_leaders", []):
                print(
                    f"{int(row.get('rank') or 0):>3}. {str(row.get('spot_ticker') or ''):<10} "
                    f"money={float(row.get('spot_session_money', 0) or 0):>16,.0f} "
                    f"pace={float(row.get('spot_money_per_minute', 0) or 0):>12,.0f}"
                )
            print()
            print("MACRO / FUTURES WATCH — НЕ ТОРГОВЫЙ SPOT-РЕЙТИНГ")
            for row in diagnostics.get("macro_watch", []):
                print(
                    f"{int(row.get('rank') or 0):>3}. {str(row.get('ticker') or ''):<10} "
                    f"dir={str(row.get('direction') or '-'):<6} "
                    f"money={float(row.get('session_money', 0) or 0):>16,.0f} "
                    f"pace={float(row.get('money_per_minute', 0) or 0):>12,.0f}"
                )
            print()
            print(
                "DIAGNOSTICS: "
                f"ALL_TQBR={diagnostics.get('stock_universe_total', 0)} "
                f"MONEY_SCREENED={diagnostics.get('stock_money_screened', 0)} "
                f"DEEP={diagnostics.get('stock_deep_analyzed', 0)} "
                f"MONEY_LEADERS={diagnostics.get('money_leader_count', 0)} "
                f"ACCEPTED={diagnostics.get('candidate_accepted', 0)} "
                f"REJECTED={diagnostics.get('candidate_rejected', 0)} "
                f"SPOT={diagnostics.get('spot_candidates', 0)} "
                f"MACRO_WATCH={diagnostics.get('macro_candidates', 0)} "
                f"SELECTED_SPOT={diagnostics.get('selected', 0)} "
                f"READY={diagnostics.get('ready', 0)} "
                f"CONFIRMED={diagnostics.get('confirmed', 0)}"
            )
            if diagnostics.get("candidate_rejections"):
                print("REJECTIONS: " + ", ".join(
                    f"{key}={value}" for key, value in sorted(diagnostics["candidate_rejections"].items())
                ))
        else:
            print("NO SPOT WATCHLIST CANDIDATES")
        print()
        print("SPOT radar: all canonical TQBR stocks are money-screened first; only the most active receive deep SPOT analysis.")
        print("Futures are not trade candidates here. After a valid SPOT scenario, the user selects the corresponding futures contract.")
        print("Macro OIL/GOLD/GAS/FX is a separate FUTURES_DIRECT watch layer and cannot become a SPOT trade signal.")
        print("Scanner is read-only: no order execution, position sizing, stop-loss or take-profit automation.")
        print("=" * 170)
