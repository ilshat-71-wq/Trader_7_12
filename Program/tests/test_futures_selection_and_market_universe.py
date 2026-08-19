import unittest
from datetime import date, timedelta

from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService
from services.market_trading_universe_service import MarketTradingUniverseService
from services.futures_trade_candidate_service import FuturesTradeCandidateService


class FuturesSelectionTests(unittest.TestCase):
    def test_keeps_nearest_two_and_excludes_expiry_within_three_days(self):
        today = date.today()
        mappings = [
            {"spot_ticker": "SBER", "futures_ticker": "OLD", "futures_expiry": (today + timedelta(days=2)).isoformat()},
            {"spot_ticker": "SBER", "futures_ticker": "NEAR", "futures_expiry": (today + timedelta(days=8)).isoformat()},
            {"spot_ticker": "SBER", "futures_ticker": "NEXT", "futures_expiry": (today + timedelta(days=35)).isoformat()},
            {"spot_ticker": "SBER", "futures_ticker": "FAR", "futures_expiry": (today + timedelta(days=70)).isoformat()},
        ]

        result = TwoPhaseFuturesMorningRadarService._select_current_contracts(mappings)
        self.assertEqual([item["futures_ticker"] for item in result], ["NEAR", "NEXT"])
        self.assertTrue(all(item["days_to_expiry"] > 3 for item in result))

    def test_macro_groups_are_target_groups(self):
        self.assertEqual(
            MarketTradingUniverseService.futures_group("BRU6"),
            MarketTradingUniverseService.OIL,
        )
        self.assertEqual(
            MarketTradingUniverseService.futures_group("GDZ6"),
            MarketTradingUniverseService.GOLD,
        )
        self.assertEqual(
            MarketTradingUniverseService.futures_group("NGU6"),
            MarketTradingUniverseService.GAS,
        )
        self.assertEqual(
            MarketTradingUniverseService.futures_group("SIU6"),
            MarketTradingUniverseService.USDRUB,
        )
        self.assertTrue(all(
            group in FuturesTradeCandidateService.TARGET_SPOT_GROUPS
            for group in MarketTradingUniverseService.MACRO_GROUPS
        ))


if __name__ == "__main__":
    unittest.main()
