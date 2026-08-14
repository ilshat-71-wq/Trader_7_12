"""
Trader_7_12 Pro

Morning Trading Pipeline v0.1 tests.
"""

from services.morning_trading_pipeline_service import MorningTradingPipelineService


class FakeRadarService:
    def __init__(self, results):
        self.results = results

    def scan(self, mappings=None):
        return list(self.results)


class FakeConfirmationService:
    def __init__(self, confirmations):
        self.confirmations = confirmations

    def analyze(self, futures_ticker, futures_class_code, spot_direction):
        return self.confirmations.get(futures_ticker)


class FakeCandidateService:
    def rank(self, radar_results, confirmations=None, limit=3):
        from services.futures_trade_candidate_service import FuturesTradeCandidateService
        service = FuturesTradeCandidateService()
        return service.rank(
            radar_results,
            confirmations=confirmations,
            limit=limit,
        )


class FakeFinalTradeService:
    def build_top(self, candidates, lot_sizes=None, limit=3):
        from services.final_trade_service import FinalTradeService
        service = FinalTradeService()
        return service.build_top(candidates, lot_sizes=lot_sizes, limit=limit)


class TestMorningTradingPipelineService:
    @staticmethod
    def radar(ticker="SRU6", spot="SBER", score=90.0, direction="LONG"):
        return {
            "status": "OK",
            "direction": direction,
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2026-09-15",
            "spot_ticker": spot,
            "spot_class_code": "SPBRU",
            "spot_price": 300.0,
            "radar_score": score,
            "relative_strength": 0.8,
            "setup": "FIRST_PULLBACK_LONG",
            "setup_direction": direction,
            "setup_state": "READY",
            "entry_trigger": 299.0,
            "previous_high": 305.0,
            "previous_low": 95.0,
        }

    @staticmethod
    def confirmation(direction="LONG", score=85, ticker="SRU6"):
        return {
            "status": "OK",
            "confirmation": "CONFIRMED",
            "direction": direction,
            "score": score,
            "money_volume": 20_000_000,
            "trade_count": 50,
            "last_price": 100.0,
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
        }

    def test_pipeline_returns_final_trade(self):
        radar = self.radar()
        confirmation = self.confirmation()

        service = MorningTradingPipelineService(
            radar_service=FakeRadarService([radar]),
            confirmation_service=FakeConfirmationService({"SRU6": confirmation}),
            candidate_service=FakeCandidateService(),
            final_trade_service=FakeFinalTradeService(),
        )

        trades = service.scan(
            mappings=[{"futures_ticker": "SRU6", "spot_ticker": "SBER"}],
            confirmations={"SRU6": confirmation},
            limit=3,
        )

        assert len(trades) == 1
        assert trades[0]["status"] == "READY"
        assert trades[0]["direction"] == "LONG"
        assert trades[0]["futures_ticker"] == "SRU6"
        assert trades[0]["pipeline_version"] == "0.2"

    def test_pipeline_rejects_blocked_confirmation(self):
        radar = self.radar()
        blocked = self.confirmation()
        blocked["status"] = "BLOCKED"

        service = MorningTradingPipelineService(
            radar_service=FakeRadarService([radar]),
            confirmation_service=FakeConfirmationService({"SRU6": blocked}),
        )

        assert service.scan(confirmations={"SRU6": blocked}) == []

    def test_pipeline_keeps_only_top_two(self):
        radars = [
            self.radar("A1U6", "SBER", 70),
            self.radar("B1U6", "LKOH", 95),
            self.radar("C1U6", "ROSN", 80),
        ]
        confirmations = {
            "A1U6": self.confirmation(ticker="A1U6", score=70),
            "B1U6": self.confirmation(ticker="B1U6", score=95),
            "C1U6": self.confirmation(ticker="C1U6", score=80),
        }

        service = MorningTradingPipelineService(
            radar_service=FakeRadarService(radars),
            confirmation_service=FakeConfirmationService(confirmations),
        )

        trades = service.scan(confirmations=confirmations, limit=2)

        assert len(trades) == 2
        assert trades[0]["futures_ticker"] == "B1U6"
        assert trades[0]["rank"] == 1
        assert trades[1]["rank"] == 2

    def test_pipeline_does_not_execute_orders(self):
        service = MorningTradingPipelineService(
            radar_service=FakeRadarService([]),
            confirmation_service=FakeConfirmationService({}),
        )

        result = service.scan(limit=3)
        assert isinstance(result, list)
        assert all("order_id" not in item for item in result)


def run_tests():
    test = TestMorningTradingPipelineService()
    tests = [
        ("test_pipeline_returns_final_trade", test.test_pipeline_returns_final_trade),
        ("test_pipeline_rejects_blocked_confirmation", test.test_pipeline_rejects_blocked_confirmation),
        ("test_pipeline_keeps_only_top_two", test.test_pipeline_keeps_only_top_two),
        ("test_pipeline_does_not_execute_orders", test.test_pipeline_does_not_execute_orders),
    ]

    print("============================================================================")
    print("TRADER_7_12 PRO - MORNING TRADING PIPELINE TEST")
    print("============================================================================")

    for name, function in tests:
        function()
        print(f"PASS {name}")

    print("============================================================================")
    print("ALL TESTS PASSED")
    print("============================================================================")


if __name__ == "__main__":
    run_tests()
