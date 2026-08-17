"""Trader_7_12 Pro - session-aware Spot-first scanner pipeline.

Pipeline:
Futures Universe / Mapping
    -> Futures Morning Radar
    -> Futures Confirmation
    -> Futures Trade Candidate Ranking

The service selects and ranks scanner candidates only. It never places orders.
"""

from api.bcs_api import BCSAPI
from services.futures_confirmation_service import FuturesConfirmationService
from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.market_session_service import MarketSessionService


class MorningTradingPipelineService:
    """Build the current-session shortlist from Spot radar and futures confirmation."""

    VERSION = "0.5"

    def __init__(self, radar_service=None, confirmation_service=None, candidate_service=None, session_service=None):
        self.radar_service = radar_service or FuturesMorningRadarService()
        self.session_service = session_service or MarketSessionService()

        if confirmation_service is None:
            api = BCSAPI()
            if not api.authorize():
                raise RuntimeError("BCS API authorization failed")
            confirmation_service = FuturesConfirmationService(api=api)
        self.confirmation_service = confirmation_service
        self.candidate_service = candidate_service or FuturesTradeCandidateService(
            confirmation_service=self.confirmation_service
        )

    def scan(self, mappings=None, confirmations=None, limit=3):
        """Run the scanner for the currently open Moscow futures session."""
        session_info = self.session_service.get_session_info()
        session = session_info.get("session", "CLOSED")

        if session not in {"MORNING", "MAIN", "EVENING"}:
            return []

        radar_results = self.radar_service.scan(mappings=mappings)
        candidates = self.candidate_service.rank(
            radar_results,
            confirmations=confirmations,
            limit=limit,
        )

        for rank, candidate in enumerate(candidates, start=1):
            candidate["pipeline_version"] = self.VERSION
            candidate["rank"] = rank
            candidate["market_session"] = session
            candidate["market_session_label"] = session_info.get("label", session)
            candidate["market_timezone"] = session_info.get("timezone", "Europe/Moscow")
            candidate["market_date"] = session_info.get("date")
            candidate["market_time"] = session_info.get("time")

        return candidates

    @staticmethod
    def print_results(results):
        print()
        print("=" * 118)
        print("TRADER_7_12 PRO - SESSION-AWARE SCANNER")
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

        if results:
            first = results[0]
            print()
            print(f"SESSION: {first.get('market_session_label', first.get('market_session', '-'))}")
            print(f"TIME: {first.get('market_date', '-')} {first.get('market_time', '-')} MSK")

        print()
        print("Pipeline: SPOT RADAR -> FUTURES CONFIRMATION -> TOP CANDIDATES")
        print("Scanner output is read-only and contains no portfolio or order operations.")
        print("=" * 118)
