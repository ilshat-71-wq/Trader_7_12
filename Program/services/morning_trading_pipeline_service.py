"""Trader_7_12 Pro - Spot-first morning scanner pipeline.

Pipeline:
Futures Universe / Mapping
    -> Futures Morning Radar
    -> Futures Confirmation
    -> Futures Trade Candidate Ranking

This service selects and ranks morning candidates only.
"""

from api.bcs_api import BCSAPI
from services.futures_confirmation_service import FuturesConfirmationService
from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService


class MorningTradingPipelineService:
    """Build the final morning shortlist from Spot radar and futures confirmation."""

    VERSION = "0.4"

    def __init__(
        self,
        radar_service=None,
        confirmation_service=None,
        candidate_service=None,
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

    def scan(self, mappings=None, confirmations=None, limit=3):
        """Run the morning scanner and return only the strongest candidates."""
        radar_results = self.radar_service.scan(mappings=mappings)

        candidates = self.candidate_service.rank(
            radar_results,
            confirmations=confirmations,
            limit=limit,
        )

        for rank, candidate in enumerate(candidates, start=1):
            candidate["pipeline_version"] = self.VERSION
            candidate["rank"] = rank

        return candidates

    @staticmethod
    def print_results(results):
        print()
        print("=" * 118)
        print("TRADER_7_12 PRO - MORNING SCANNER")
        print("=" * 118)
        print()
        print(
            f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}"
            f"{'DIR':<8}{'FUTURES PRICE':>14}{'RADAR':>9}"
            f"{'CONF':>9}{'RS':>9}{'MONEY VOL':>16}{'SCORE':>9}"
        )
        print("-" * 118)

        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('futures_ticker', '-'): <12}"
                f"{item.get('spot_ticker', '-'): <9}"
                f"{item.get('direction', '-'): <8}"
                f"{float(item.get('futures_price', 0) or 0):>14.4f}"
                f"{float(item.get('radar_score', 0) or 0):>9.2f}"
                f"{float(item.get('confirmation_score', 0) or 0):>9.2f}"
                f"{float(item.get('relative_strength', 0) or 0):>9.2f}"
                f"{float(item.get('money_volume', 0) or 0):>16,.0f}"
                f"{float(item.get('candidate_score', 0) or 0):>9.2f}"
            )

        print()
        print("Pipeline: SPOT RADAR -> FUTURES CONFIRMATION -> TOP CANDIDATES")
        print("Scanner output is read-only and contains no portfolio or order operations.")
        print("=" * 118)
