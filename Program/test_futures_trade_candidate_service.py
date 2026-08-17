from services.futures_trade_candidate_service import FuturesTradeCandidateService


class TestFuturesTradeCandidateService:

    @staticmethod
    def radar(
        ticker,
        direction="LONG",
        radar_score=70,
        rs=0.20,
        spot_ticker=None,
        spot_money=0,
        spot_group=None,
        expiry="2026-09-15",
    ):
        return {
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
            "futures_expiry": expiry,
            "spot_ticker": spot_ticker or ticker[:2],
            "spot_class_code": "SPBRU",
            "spot_name": "",
            "spot_type": "",
            "spot_group": spot_group,
            "direction": direction,
            "radar_score": radar_score,
            "relative_strength": rs,
            "spot_money_volume": spot_money,
            "spot_money_ratio": 1.0,
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
            self.radar("MEU6", spot_ticker="MOEX", spot_group="MOEX_STOCK"),
            self.confirmation(),
        )
        assert result is not None
        assert result["status"] == "READY"
        assert result["direction"] == "LONG"
        assert result["spot_group"] == "MOEX_STOCK"

    def test_non_target_spot_is_rejected(self):
        service = FuturesTradeCandidateService()
        result = service.build_candidate(
            self.radar("SRU6", spot_ticker="SBER"),
            self.confirmation(),
        )
        assert result is None

    def test_conflicting_confirmation_is_rejected(self):
        service = FuturesTradeCandidateService()
        result = service.build_candidate(
            self.radar("MEU6", spot_ticker="MOEX", spot_group="MOEX_STOCK"),
            self.confirmation(direction="SHORT"),
        )
        assert result is None

    def test_blocked_confirmation_is_rejected(self):
        service = FuturesTradeCandidateService()
        blocked = self.confirmation()
        blocked["status"] = "BLOCKED"
        result = service.build_candidate(
            self.radar("MEU6", spot_ticker="MOEX", spot_group="MOEX_STOCK"),
            blocked,
        )
        assert result is None

    def test_one_money_leader_is_selected_per_target_group(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar(
                "MEU6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                radar_score=60,
                spot_money=200_000_000,
            ),
            self.radar(
                "NGU6",
                spot_ticker="NG",
                spot_group="GAS",
                radar_score=80,
                spot_money=150_000_000,
            ),
            self.radar(
                "BRU6",
                spot_ticker="BR",
                spot_group="OIL",
                radar_score=90,
                spot_money=100_000_000,
            ),
            self.radar(
                "SIU6",
                spot_ticker="USDRUB",
                spot_group="USD",
                radar_score=70,
                spot_money=80_000_000,
            ),
            self.radar(
                "GDU6",
                spot_ticker="GOLD",
                spot_group="GOLD",
                radar_score=75,
                spot_money=50_000_000,
            ),
            self.radar(
                "MOX6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                radar_score=95,
                spot_money=120_000_000,
            ),
        ]
        confirmations = {
            ticker: self.confirmation(score=90)
            for ticker in {item["futures_ticker"] for item in radars}
        }

        result = service.rank(radars, confirmations, limit=5)

        assert [item["spot_group"] for item in result] == [
            "MOEX_STOCK",
            "GAS",
            "OIL",
            "USD",
            "GOLD",
        ]
        assert result[0]["futures_ticker"] == "MEU6"
        assert result[0]["spot_money_volume"] == 200_000_000

    def test_current_spot_money_beats_radar_score(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar(
                "MEU6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                radar_score=60,
                spot_money=200_000_000,
            ),
            self.radar(
                "NGU6",
                spot_ticker="NG",
                spot_group="GAS",
                radar_score=99,
                spot_money=100_000_000,
            ),
        ]
        confirmations = {
            "MEU6": self.confirmation(score=60),
            "NGU6": self.confirmation(score=99),
        }

        result = service.rank(radars, confirmations, limit=2)
        assert [item["spot_ticker"] for item in result] == ["MOEX", "NG"]

    def test_one_most_liquid_futures_per_spot(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar(
                "ALU6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                spot_money=80_000_000,
            ),
            self.radar(
                "ALZ6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                spot_money=80_000_000,
            ),
            self.radar(
                "NGU6",
                spot_ticker="NG",
                spot_group="GAS",
                spot_money=20_000_000,
            ),
        ]
        confirmations = {
            "ALU6": self.confirmation(score=90, money=120_000_000, trades=300),
            "ALZ6": self.confirmation(score=95, money=80_000_000, trades=200),
            "NGU6": self.confirmation(score=85, money=20_000_000, trades=50),
        }

        result = service.rank(radars, confirmations, limit=5)
        assert len(result) == 2
        moex = next(item for item in result if item["spot_ticker"] == "MOEX")
        assert moex["futures_ticker"] == "ALU6"

    def test_contract_with_three_or_fewer_days_to_expiry_is_rejected(self):
        service = FuturesTradeCandidateService()
        result = service.build_candidate(
            self.radar(
                "MEU6",
                spot_ticker="MOEX",
                spot_group="MOEX_STOCK",
                expiry="2026-08-19",
            ),
            self.confirmation(),
        )
        assert result is None

    def test_limit_returns_top_two(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar("MEU6", spot_ticker="MOEX", spot_group="MOEX_STOCK", spot_money=30_000_000),
            self.radar("NGU6", spot_ticker="NG", spot_group="GAS", spot_money=50_000_000),
            self.radar("BRU6", spot_ticker="BR", spot_group="OIL", spot_money=40_000_000),
        ]
        confirmations = {
            "MEU6": self.confirmation(score=60),
            "NGU6": self.confirmation(score=90),
            "BRU6": self.confirmation(score=80),
        }

        result = service.rank(radars, confirmations, limit=2)
        assert len(result) == 2
        assert [item["rank"] for item in result] == [1, 2]

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
        test.test_non_target_spot_is_rejected,
        test.test_conflicting_confirmation_is_rejected,
        test.test_blocked_confirmation_is_rejected,
        test.test_one_money_leader_is_selected_per_target_group,
        test.test_current_spot_money_beats_radar_score,
        test.test_one_most_liquid_futures_per_spot,
        test.test_contract_with_three_or_fewer_days_to_expiry_is_rejected,
        test.test_limit_returns_top_two,
        test.test_invalid_limit,
    ]

    for fn in tests:
        fn()
        print("PASS", fn.__name__)

    print("ALL TESTS PASSED")