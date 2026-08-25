from services.futures_trade_candidate_service import FuturesTradeCandidateService


class TestFuturesTradeCandidateService:
    @staticmethod
    def radar(
        ticker,
        spot_ticker,
        direction="LONG",
        spot_group="MOEX_STOCK",
        rs=0.5,
        activity=2.0,
        money=200_000_000,
        setup_state="WAIT",
        setup_quality=0.0,
        event_risk=False,
    ):
        return {
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2026-09-15",
            "spot_ticker": spot_ticker,
            "spot_class_code": "TQBR",
            "spot_name": "",
            "spot_type": "",
            "spot_group": spot_group,
            "direction": direction,
            "radar_score": 80.0,
            "relative_strength": rs,
            "relative_strength_status": "OK",
            "spot_money_volume": money,
            "spot_money_ratio": activity,
            "spot_session_activity_ratio": activity,
            "spot_money_per_minute": 20_000_000,
            "change_percent": 1.0 if direction == "LONG" else -1.0,
            "setup": "FIRST_PULLBACK",
            "setup_direction": direction,
            "setup_state": setup_state,
            "setup_phase": "SETUP_READY" if setup_state != "WAIT" else "SETUP_SCAN",
            "setup_quality_score": setup_quality,
            "moex_event_risk": event_risk,
        }

    def test_wait_is_valid_watchlist_candidate(self):
        result = FuturesTradeCandidateService.build_candidate(
            self.radar("SBERU6", "SBER", setup_state="WAIT")
        )
        assert result is not None
        assert result["status"] == "READY"
        assert result["setup_state"] == "WAIT"

    def test_ready_state_is_preserved(self):
        result = FuturesTradeCandidateService.build_candidate(
            self.radar("SBERU6", "SBER", setup_state="READY", setup_quality=75)
        )
        assert result is not None
        assert result["setup_state"] == "READY"
        assert result["setup_quality_score"] == 75.0

    def test_event_risk_is_rejected(self):
        result = FuturesTradeCandidateService.build_candidate(
            self.radar("SBERU6", "SBER", event_risk=True)
        )
        assert result is None

    def test_long_requires_positive_rs(self):
        assert FuturesTradeCandidateService.build_candidate(
            self.radar("SBERU6", "SBER", direction="LONG", rs=-0.1)
        ) is None

    def test_short_requires_negative_rs(self):
        assert FuturesTradeCandidateService.build_candidate(
            self.radar("SBERU6", "SBER", direction="SHORT", rs=0.1)
        ) is None

    def test_setup_error_is_rejected(self):
        radar = self.radar("SBERU6", "SBER")
        radar["setup_error"] = "ReadTimeout"
        assert FuturesTradeCandidateService.build_candidate(radar) is None

    def test_no_session_candles_is_rejected(self):
        radar = self.radar("SBERU6", "SBER")
        radar["setup_phase"] = "NO_SESSION_CANDLES"
        assert FuturesTradeCandidateService.build_candidate(radar) is None

    def test_target_groups_are_supported(self):
        for group, ticker in (
            ("MOEX_STOCK", "SBER"),
            ("OIL", "BR"),
            ("GOLD", "GOLD"),
            ("GAS", "NG"),
            ("USDRUB", "USD000SMALL"),
        ):
            radar = self.radar(f"{ticker}U6", ticker, spot_group=group)
            assert FuturesTradeCandidateService.build_candidate(radar) is not None

    def test_rank_returns_top_three_by_opportunity_inputs(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar("A1U6", "A", activity=3.0, money=300_000_000),
            self.radar("B1U6", "B", activity=2.0, money=200_000_000),
            self.radar("C1U6", "C", activity=1.5, money=150_000_000),
            self.radar("D1U6", "D", activity=1.0, money=100_000_000),
        ]
        result = service.rank(radars, limit=3)
        assert len(result) == 3
        assert [item["rank"] for item in result] == [1, 2, 3]

    def test_rank_none_returns_full_deep_shortlist(self):
        service = FuturesTradeCandidateService()
        radars = [
            self.radar("A1U6", "A", activity=3.0),
            self.radar("B1U6", "B", activity=2.0),
            self.radar("C1U6", "C", activity=1.5),
            self.radar("D1U6", "D", activity=1.0),
        ]
        result = service.rank(radars, limit=None)
        assert len(result) == 4
        assert [item["spot_ticker"] for item in result] == ["A", "B", "C", "D"]

    def test_invalid_limit(self):
        try:
            FuturesTradeCandidateService().rank([], limit=-1)
        except ValueError:
            return
        raise AssertionError("negative limit must raise ValueError")


if __name__ == "__main__":
    test = TestFuturesTradeCandidateService()
    for name in dir(test):
        if name.startswith("test_"):
            fn = getattr(test, name)
            fn()
            print("PASS", name)
