"""
Trader_7_12 Pro

Morning Trading Pipeline scanner-only tests.
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
            "price_change_percent": 1.0,
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
        }

    def service(self, radars, confirmations):
        return MorningTradingPipelineService(
            radar_service=FakeRadarService(radars),
            confirmation_service=FakeConfirmationService(confirmations),
            candidate_service=FakeCandidateService(),
        )

    def test_pipeline_returns_candidate(self):
        radar = self.radar()
        confirmation = self.confirmation()

        candidates = self.service([radar], {"SRU6": confirmation}).scan(
            mappings=[{"futures_ticker": "SRU6", "spot_ticker": "SBER"}],
            confirmations={"SRU6": confirmation},
            limit=3,
        )

        assert len(candidates) == 1
        assert candidates[0]["status"] == "READY"
        assert candidates[0]["direction"] == "LONG"
        assert candidates[0]["futures_ticker"] == "SRU6"
        assert candidates[0]["pipeline_version"] == MorningTradingPipelineService.VERSION
        assert candidates[0]["pipeline_version"] == "0.4"
        assert candidates[0]["rank"] == 1
        assert "stop_loss" not in candidates[0]
        assert "take_profit" not in candidates[0]
        assert "quantity" not in candidates[0]
        assert "risk_utilization" not in candidates[0]
        assert "order_id" not in candidates[0]

    def test_pipeline_rejects_blocked_confirmation(self):
        radar = self.radar()
        blocked = self.confirmation()
        blocked["status"] = "BLOCKED"

        assert self.service([radar], {"SRU6": blocked}).scan(
            confirmations={"SRU6": blocked}
        ) == []

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

        candidates = self.service(radars, confirmations).scan(
            confirmations=confirmations,
            limit=2,
        )

        assert len(candidates) == 2
        assert candidates[0]["futures_ticker"] == "B1U6"
        assert candidates[0]["rank"] == 1
        assert candidates[1]["rank"] == 2

    def test_pipeline_does_not_execute_orders(self):
        result = self.service([], {}).scan(limit=3)
        assert isinstance(result, list)
        assert all("order_id" not in item for item in result)


def run_tests():
    test = TestMorningTradingPipelineService()
    tests = [
        ("test_pipeline_returns_candidate", test.test_pipeline_returns_candidate),
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
