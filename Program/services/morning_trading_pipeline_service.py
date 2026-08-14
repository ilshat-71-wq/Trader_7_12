"""
Trader_7_12 Pro

Morning Trading Pipeline v0.1

Single orchestration layer for the Spot-first morning trading architecture.

Pipeline:
Futures Universe / Mapping
    -> Futures Morning Radar
    -> Futures Confirmation
    -> Futures Trade Candidate
    -> Trade Plan
    -> Final Trade

This service only orchestrates existing services. It does not duplicate their
business rules and it does not place orders.
"""

from api.bcs_api import BCSAPI
from services.futures_confirmation_service import FuturesConfirmationService
from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.final_trade_service import FinalTradeService


class MorningTradingPipelineService:
    """Build the final morning shortlist from the existing services."""

    VERSION = "0.2"

    def __init__(
        self,
        radar_service=None,
        confirmation_service=None,
        candidate_service=None,
        final_trade_service=None,
    ):
        self.radar_service = radar_service or FuturesMorningRadarService()

        if confirmation_service is None:
            api = BCSAPI()
            if not api.authorize():
                raise RuntimeError("BCS API authorization failed")
            confirmation_service = FuturesConfirmationService(api=api)
        self.confirmation_service = confirmation_service

        self.candidate_service = (
            candidate_service
            or FuturesTradeCandidateService(
                confirmation_service=self.confirmation_service
            )
        )
        self.final_trade_service = final_trade_service or FinalTradeService()

    def scan(
        self,
        mappings=None,
        confirmations=None,
        lot_sizes=None,
        limit=3,
    ):
        """Run the complete morning pipeline and return final trades."""
        radar_results = self.radar_service.scan(mappings=mappings)

        candidates = self.candidate_service.rank(
            radar_results,
            confirmations=confirmations,
            limit=None,
        )

        final_trades = self.final_trade_service.build_top(
            candidates,
            lot_sizes=lot_sizes,
            limit=limit,
        )

        for rank, trade in enumerate(final_trades, start=1):
            trade["pipeline_version"] = self.VERSION
            trade["rank"] = rank

        return final_trades

    @staticmethod
    def print_results(results):
        print()
        print("=" * 110)
        print("TRADER_7_12 PRO - MORNING TRADING PIPELINE")
        print("=" * 110)
        print()
        print(
            f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}"
            f"{'DIR':<8}{'ENTRY':>12}{'STOP':>12}"
            f"{'TARGET':>12}{'RR':>8}{'SCORE':>9}"
        )
        print("-" * 110)

        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('futures_ticker', '-'): <12}"
                f"{item.get('spot_ticker', '-'): <9}"
                f"{item.get('direction', '-'): <8}"
                f"{float(item.get('entry', 0) or 0):>12.4f}"
                f"{float(item.get('stop_loss', 0) or 0):>12.4f}"
                f"{float(item.get('take_profit', 0) or 0):>12.4f}"
                f"{float(item.get('rr_ratio', 0) or 0):>8.2f}"
                f"{float(item.get('candidate_score', 0) or 0):>9.2f}"
            )

        print()
        print("Pipeline: SPOT RADAR -> FUTURES CONFIRMATION -> FINAL TRADE")
        print("No order execution is performed by this service.")
        print("=" * 110)
