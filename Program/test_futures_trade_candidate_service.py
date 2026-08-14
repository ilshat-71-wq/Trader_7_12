from services.futures_trade_candidate_service import FuturesTradeCandidateService


class TestFuturesTradeCandidateService:

    @staticmethod
    def radar(ticker, direction="LONG", radar_score=70, rs=0.20):
        return {
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2026-09-15",
            "spot_ticker": ticker[:2],
            "spot_class_code": "SPBRU",
            "direction": direction,
            "radar_score": radar_score,
            "relative_strength": rs,
        }

    @staticmethod
    def confirmation(direction="LONG", score=80, money=20_000_000, trades=40):
        return {
            "status": "OK",
            "confirmation": "CONFIRMED",
            "direction": direction,
            "score": score,
            "money_volume": money,
            "trade_count": trades,
        }

    def test_build_ready_candidate(self):
        service = FuturesTradeCandidateService()
        result = service.build_candidate(
            self.radar("SRU6"),
            self.confirmation(),
        )
        assert result is not None
        assert result["status"] == "READY"
        assert result["direction"] == "LONG"
        assert result["candidate_score"] > 0

    def test_conflicting_confirmation_is_rejected(self):
        service = FuturesTradeCandidateService()
        result = service.build_candidate(
            self.radar("SRU6", direction="LONG"),
            self.confirmation(direction="SHORT"),
        )
        assert result is None

    def test_blocked_confirmation_is_rejected(self):
        service = FuturesTradeCandidateService()
        blocked = self.confirmation()
        blocked["status"] = "BLOCKED"
        result = service.build_candidate(self.radar("SRU6"), blocked)
        assert result is None

    def test_rank_orders_by_candidate_score(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar("SRU6", radar_score=60),
            self.radar("LKU6", radar_score=90, rs=0.40),
            self.radar("RNU6", radar_score=75),
        ]
        confirmations = {
            "SRU6": self.confirmation(score=60),
            "LKU6": self.confirmation(score=95, money=100_000_000),
            "RNU6": self.confirmation(score=75),
        }

        result = service.rank(radars, confirmations, limit=3)
        assert len(result) == 3
        assert result[0]["futures_ticker"] == "LKU6"
        assert [item["rank"] for item in result] == [1, 2, 3]

    def test_limit_returns_top_two(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar("SRU6", radar_score=60),
            self.radar("LKU6", radar_score=90),
            self.radar("RNU6", radar_score=80),
        ]
        confirmations = {
            "SRU6": self.confirmation(score=60),
            "LKU6": self.confirmation(score=90),
            "RNU6": self.confirmation(score=80),
        }

        result = service.rank(radars, confirmations, limit=2)
        assert len(result) == 2
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2

    def test_invalid_limit(self):
        service = FuturesTradeCandidateService()
        try:
            service.rank([], {}, limit=-1)
        except ValueError:
            return
        raise AssertionError("negative limit must raise ValueError")


if __name__ == "__main__":
    test = TestFuturesTradeCandidateService()
    tests = [
        test.test_build_ready_candidate,
        test.test_conflicting_confirmation_is_rejected,
        test.test_blocked_confirmation_is_rejected,
        test.test_rank_orders_by_candidate_score,
        test.test_limit_returns_top_two,
        test.test_invalid_limit,
    ]

    print("============================================================================")
    print("TRADER_7_12 PRO - FUTURES TRADE CANDIDATE SERVICE TEST")
    print("============================================================================")

    for fn in tests:
        fn()
        print("PASS", fn.__name__)

    print()
    print("ALL TESTS PASSED")
    print("============================================================================")
