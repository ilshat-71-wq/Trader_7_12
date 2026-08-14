from services.trade_plan_service import TradePlanService


class TestTradePlanService:

    @staticmethod
    def candidate(direction="LONG", futures_price=100.0):
        return {
            "status": "READY",
            "direction": direction,
            "futures_ticker": "SRU6",
            "futures_class_code": "SPBFUT",
            "spot_ticker": "SBER",
            "spot_price": 350.0,
            "setup": "FIRST_PULLBACK_LONG",
            "setup_state": "READY",
            "entry_trigger": 348.0,
            "previous_high": 352.0,
            "previous_low": 98.0,
            "futures_price": futures_price,
            "candidate_score": 82.5,
        }

    def test_long_plan(self):
        service = TradePlanService()
        result = service.generate_candidate_plan(self.candidate())

        assert result["trade_plan"] is True
        assert result["direction"] == "LONG"
        assert result["entry"] == 100.0
        assert result["stop_loss"] == 98.0
        assert result["take_profit"] == 104.0
        assert result["rr_ratio"] == 2.0

    def test_short_plan(self):
        service = TradePlanService()
        result = service.generate_candidate_plan(
            self.candidate(
                direction="SHORT",
                futures_price=100.0,
            )
            | {
                "setup": "FIRST_REBOUND_SHORT",
                "previous_high": 102.0,
                "previous_low": 98.0,
            }
        )

        assert result["trade_plan"] is True
        assert result["direction"] == "SHORT"
        assert result["entry"] == 100.0
        assert result["stop_loss"] == 102.0
        assert result["take_profit"] == 96.0
        assert result["rr_ratio"] == 2.0

    def test_invalid_candidate_is_rejected(self):
        service = TradePlanService()
        result = service.generate_candidate_plan({"status": "BLOCKED"})
        assert result["trade_plan"] is False

    def test_missing_futures_price_is_rejected(self):
        service = TradePlanService()
        candidate = self.candidate()
        candidate["futures_price"] = 0
        result = service.generate_candidate_plan(candidate)
        assert result["trade_plan"] is False

    def test_legacy_plan_remains_available(self):
        service = TradePlanService()
        result = service.generate_plan(
            current_price=100.0,
            signal="STRONG_LONG",
            momentum_score=70,
            breakout_score=50,
        )
        assert result["trade_plan"] is True
        assert result["direction"] == "LONG"
        assert result["rr_ratio"] == 3.0


if __name__ == "__main__":
    test = TestTradePlanService()
    tests = [
        test.test_long_plan,
        test.test_short_plan,
        test.test_invalid_candidate_is_rejected,
        test.test_missing_futures_price_is_rejected,
        test.test_legacy_plan_remains_available,
    ]

    print("============================================================================")
    print("TRADER_7_12 PRO - TRADE PLAN SERVICE TEST")
    print("============================================================================")

    for fn in tests:
        fn()
        print("PASS", fn.__name__)

    print()
    print("ALL TESTS PASSED")
    print("============================================================================")
