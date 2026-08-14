"""
Trader_7_12 Pro

Final Trade Service v0.2 tests.
"""

from services.final_trade_service import FinalTradeService


class TestFinalTradeService:
    def setup_method(self):
        self.service = FinalTradeService(
            deposit=1_000_000,
            risk_percent=1.0,
            min_rr=1.5,
            max_position_percent=20.0,
        )

    @staticmethod
    def candidate(**overrides):
        value = {
            "status": "READY",
            "direction": "LONG",
            "futures_ticker": "SRU6",
            "futures_class_code": "SPBFUT",
            "spot_ticker": "SBER",
            "futures_price": 100.0,
            "spot_price": 300.0,
            "setup": "FIRST_PULLBACK_LONG",
            "setup_state": "READY",
            "entry_trigger": 299.0,
            "previous_high": 305.0,
            "previous_low": 295.0,
            "candidate_score": 88.0,
            "radar_score": 90.0,
            "confirmation_score": 85.0,
            "relative_strength": 0.8,
        }
        value.update(overrides)
        return value

    def test_build_ready_final_trade(self):
        trade = self.service.build(self.candidate(), lot_size=1)

        assert trade is not None
        assert trade["status"] == "READY"
        assert trade["direction"] == "LONG"
        assert trade["futures_ticker"] == "SRU6"
        assert trade["entry"] == 100.0
        assert trade["stop_loss"] == 95.0
        assert trade["take_profit"] == 110.0
        assert trade["rr_ratio"] == 2.0
        assert trade["quantity"] > 0
        assert trade["actual_risk_amount"] <= 10_000

    def test_short_final_trade(self):
        trade = self.service.build(
            self.candidate(
                direction="SHORT",
                setup="FIRST_REBOUND_SHORT",
                previous_high=105.0,
                previous_low=95.0,
            )
        )

        assert trade is not None
        assert trade["direction"] == "SHORT"
        assert trade["stop_loss"] == 105.0
        assert trade["take_profit"] == 90.0

    def test_not_ready_candidate_is_rejected(self):
        assert self.service.build(self.candidate(status="BLOCKED")) is None

    def test_invalid_direction_is_rejected(self):
        assert self.service.build(self.candidate(direction="NONE")) is None

    def test_invalid_futures_price_is_rejected(self):
        assert self.service.build(self.candidate(futures_price=0)) is None

    def test_position_respects_lot_size(self):
        trade = self.service.build(self.candidate(), lot_size=10)

        assert trade is not None
        assert trade["quantity"] % 10 == 0
        assert trade["lots"] >= 1

    def test_build_top_sorts_and_limits(self):
        candidates = [
            self.candidate(
                futures_ticker="LKU6",
                candidate_score=70,
            ),
            self.candidate(
                futures_ticker="SRU6",
                candidate_score=95,
            ),
            self.candidate(
                futures_ticker="GDU6",
                candidate_score=80,
            ),
        ]

        trades = self.service.build_top(candidates, limit=2)

        assert len(trades) == 2
        assert trades[0]["futures_ticker"] == "SRU6"
        assert trades[0]["rank"] == 1
        assert trades[1]["rank"] == 2

    def test_build_top_skips_invalid_candidates(self):
        candidates = [
            self.candidate(status="BLOCKED"),
            self.candidate(futures_ticker="SRU6", candidate_score=90),
        ]

        trades = self.service.build_top(candidates, limit=3)

        assert len(trades) == 1
        assert trades[0]["futures_ticker"] == "SRU6"


def run_tests():
    test = TestFinalTradeService()
    tests = [
        ("test_build_ready_final_trade", test.test_build_ready_final_trade),
        ("test_short_final_trade", test.test_short_final_trade),
        ("test_not_ready_candidate_is_rejected", test.test_not_ready_candidate_is_rejected),
        ("test_invalid_direction_is_rejected", test.test_invalid_direction_is_rejected),
        ("test_invalid_futures_price_is_rejected", test.test_invalid_futures_price_is_rejected),
        ("test_position_respects_lot_size", test.test_position_respects_lot_size),
        ("test_build_top_sorts_and_limits", test.test_build_top_sorts_and_limits),
        ("test_build_top_skips_invalid_candidates", test.test_build_top_skips_invalid_candidates),
    ]

    print("============================================================================")
    print("TRADER_7_12 PRO - FINAL TRADE SERVICE TEST")
    print("============================================================================")

    for name, function in tests:
        function()
        print(f"PASS {name}")

    print("============================================================================")
    print("ALL TESTS PASSED")
    print("============================================================================")


if __name__ == "__main__":
    run_tests()
