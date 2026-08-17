from services.morning_trading_pipeline_service import MorningTradingPipelineService


class FakeSessionService:
    def __init__(self, session="MORNING"):
        self.session = session

    def get_session_info(self):
        labels = {"MORNING": "УТРЕННЯЯ СЕССИЯ", "MAIN": "ОСНОВНАЯ СЕССИЯ", "EVENING": "ВЕЧЕРНЯЯ СЕССИЯ"}
        return {"timezone": "Europe/Moscow", "date": "2026-08-17", "time": "20:30:00" if self.session == "EVENING" else "08:30:00", "session": self.session, "label": labels[self.session], "market_open": True}


class FakeRadarService:
    def __init__(self, results): self.results = results
    def scan(self, mappings=None): return list(self.results)


class FakeConfirmationService:
    def __init__(self, confirmations): self.confirmations = confirmations
    def analyze(self, futures_ticker, futures_class_code, spot_direction): return self.confirmations.get(futures_ticker)


class FakeCandidateService:
    def rank(self, radar_results, confirmations=None, limit=3):
        from services.futures_trade_candidate_service import FuturesTradeCandidateService
        return FuturesTradeCandidateService().rank(radar_results, confirmations=confirmations, limit=limit)


class TestMorningTradingPipelineService:
    @staticmethod
    def radar(ticker="SRU6", spot="MOEX", score=90.0, direction="LONG", spot_group="MOEX_STOCK", spot_money_volume=200_000_000, spot_money_ratio=2.0, spot_session_activity_ratio=2.0):
        return {"status": "OK", "direction": direction, "futures_ticker": ticker, "futures_class_code": "SPBFUT", "futures_expiry": "2026-09-15", "spot_ticker": spot, "spot_class_code": "SPBRU", "spot_price": 300.0, "radar_score": score, "relative_strength": 0.8, "setup": "FIRST_PULLBACK", "setup_direction": direction, "setup_state": "READY", "entry_trigger": 299.0, "previous_high": 305.0, "previous_low": 95.0, "spot_money_volume": spot_money_volume, "spot_money_ratio": spot_money_ratio, "spot_session_activity_ratio": spot_session_activity_ratio, "spot_group": spot_group}

    @staticmethod
    def confirmation(direction="LONG", score=85, ticker="SRU6", price_change_percent=1.0):
        return {"status": "OK", "confirmation": "CONFIRMED", "direction": direction, "score": score, "money_volume": 20_000_000, "trade_count": 50, "last_price": 100.0, "price_change_percent": price_change_percent, "futures_ticker": ticker, "futures_class_code": "SPBFUT"}

    def service(self, radars, confirmations, session="MORNING"):
        return MorningTradingPipelineService(radar_service=FakeRadarService(radars), confirmation_service=FakeConfirmationService(confirmations), candidate_service=FakeCandidateService(), session_service=FakeSessionService(session))

    def test_pipeline_returns_candidate_with_session_metadata(self):
        radar = self.radar(); confirmation = self.confirmation()
        candidates = self.service([radar], {"SRU6": confirmation}).scan(mappings=[{"futures_ticker": "SRU6", "spot_ticker": "MOEX"}], confirmations={"SRU6": confirmation}, limit=3)
        assert len(candidates) == 1
        assert candidates[0]["status"] == "READY"
        assert candidates[0]["pipeline_version"] == "0.7"
        assert candidates[0]["market_session"] == "MORNING"
        assert candidates[0]["market_time"] == "08:30:00"
        assert candidates[0]["session_strategy"] == "ИМПУЛЬС / АКТИВНОСТЬ / ПЕРВЫЙ ДВИЖ"
        assert candidates[0]["spot_session_activity_ratio"] == 2.0
        assert candidates[0]["session_rank_score"] > 0
        assert candidates[0]["rank"] == 1
        assert "stop_loss" not in candidates[0] and "take_profit" not in candidates[0] and "quantity" not in candidates[0] and "order_id" not in candidates[0]

    def test_pipeline_rejects_blocked_confirmation(self):
        radar = self.radar(); blocked = self.confirmation(); blocked["status"] = "BLOCKED"
        assert self.service([radar], {"SRU6": blocked}).scan(confirmations={"SRU6": blocked}) == []

    def test_pipeline_keeps_only_top_two(self):
        radars = [self.radar("A1U6", "MOEX", 70, "LONG", "MOEX_STOCK", 100_000_000, 1.0, 1.0), self.radar("B1U6", "BR", 95, "LONG", "OIL", 300_000_000, 3.0, 3.0), self.radar("C1U6", "NG", 80, "LONG", "GAS", 200_000_000, 2.0, 2.0)]
        confirmations = {"A1U6": self.confirmation(ticker="A1U6", score=70), "B1U6": self.confirmation(ticker="B1U6", score=95), "C1U6": self.confirmation(ticker="C1U6", score=80)}
        candidates = self.service(radars, confirmations).scan(confirmations=confirmations, limit=2)
        assert len(candidates) == 2 and candidates[0]["futures_ticker"] == "B1U6" and candidates[0]["rank"] == 1 and candidates[1]["futures_ticker"] == "C1U6" and candidates[1]["rank"] == 2

    def test_evening_profile_uses_confirmation_and_activity(self):
        radars = [self.radar("A1U6", "MOEX", 95, "LONG", "MOEX_STOCK", 100_000_000, 1.0, 1.0), self.radar("B1U6", "BR", 80, "LONG", "OIL", 100_000_000, 5.0, 4.0)]
        confirmations = {"A1U6": self.confirmation(ticker="A1U6", score=70), "B1U6": self.confirmation(ticker="B1U6", score=95)}
        candidates = self.service(radars, confirmations, "EVENING").scan(confirmations=confirmations, limit=2)
        assert len(candidates) == 2 and candidates[0]["market_session"] == "EVENING" and candidates[0]["futures_ticker"] == "B1U6" and candidates[0]["session_strategy"] == "ВЕЧЕРНИЙ ИМПУЛЬС / ПОДТВЕРЖДЕНИЕ / АКТИВНОСТЬ"

    def test_evening_activity_can_beat_higher_raw_radar(self):
        radars = [self.radar("A1U6", "MOEX", 95, "LONG", "MOEX_STOCK", 100_000_000, 1.0, 0.5), self.radar("B1U6", "BR", 82, "LONG", "OIL", 100_000_000, 1.0, 3.0)]
        confirmations = {"A1U6": self.confirmation(ticker="A1U6", score=70), "B1U6": self.confirmation(ticker="B1U6", score=90)}
        candidates = self.service(radars, confirmations, "EVENING").scan(confirmations=confirmations, limit=2)
        assert candidates[0]["futures_ticker"] == "B1U6"
        assert candidates[0]["session_rank_score"] > candidates[1]["session_rank_score"]

    def test_pipeline_does_not_execute_orders(self):
        result = self.service([], {}).scan(limit=3)
        assert isinstance(result, list) and all("order_id" not in item for item in result)


def run_tests():
    test = TestMorningTradingPipelineService()
    tests = [test.test_pipeline_returns_candidate_with_session_metadata, test.test_pipeline_rejects_blocked_confirmation, test.test_pipeline_keeps_only_top_two, test.test_evening_profile_uses_confirmation_and_activity, test.test_evening_activity_can_beat_higher_raw_radar, test.test_pipeline_does_not_execute_orders]
    for function in tests:
        function(); print("PASS", function.__name__)
    print("ALL TESTS PASSED")


if __name__ == "__main__": run_tests()
