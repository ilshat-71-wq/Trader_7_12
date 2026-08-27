from services.morning_trading_pipeline_service import MorningTradingPipelineService


class FakeSessionService:
    def __init__(self, session="MORNING"):
        self.session = session

    def get_session_info(self):
        return {"timezone": "Europe/Moscow", "date": "2026-08-25", "time": "08:30:00", "session": self.session, "label": self.session, "market_open": True}


class FakeRadarService:
    def __init__(self, results):
        self.results = results

    def scan(self, mappings=None):
        return list(self.results)


class FakeCandidateService:
    def rank(self, radar_results, confirmations=None, limit=3):
        from services.futures_trade_candidate_service import FuturesTradeCandidateService
        return FuturesTradeCandidateService().rank(radar_results, confirmations=confirmations, limit=limit)


class TestMorningTradingPipelineService:
    @staticmethod
    def radar(ticker="SRU6", spot="SBER", score=90.0, direction="LONG", spot_group="MOEX_STOCK", spot_money_volume=200_000_000, spot_money_ratio=2.0, spot_session_activity_ratio=2.0, setup_state="WAIT", rs=0.8, spot_price=300.0, entry_trigger=299.0):
        return {
            "status": "OK", "direction": direction, "futures_ticker": ticker, "futures_class_code": "SPBFUT", "futures_expiry": "2026-09-15",
            "spot_ticker": spot, "spot_class_code": "TQBR", "spot_price": spot_price, "radar_score": score, "relative_strength": rs,
            "relative_strength_status": "OK", "relative_strength_signal": "STRONGER" if rs > 0 else "WEAKER",
            "setup": "FIRST_PULLBACK" if direction == "LONG" else "FIRST_REBOUND", "setup_direction": direction, "setup_state": setup_state,
            "setup_quality_score": 70.0 if setup_state != "WAIT" else 0.0, "setup_phase": "SETUP_READY" if setup_state != "WAIT" else "SETUP_SCAN",
            "entry_trigger": entry_trigger, "previous_high": 305.0, "previous_low": 295.0, "spot_money_volume": spot_money_volume,
            "spot_money_ratio": spot_money_ratio, "spot_session_activity_ratio": spot_session_activity_ratio, "spot_money_per_minute": 10_000_000,
            "spot_change_percent": 1.0 if direction == "LONG" else -1.0, "spot_group": spot_group, "moex_event_risk": False,
        }

    @staticmethod
    def service(radars, session="MORNING"):
        return MorningTradingPipelineService(radar_service=FakeRadarService(radars), candidate_service=FakeCandidateService(), session_service=FakeSessionService(session))

    def test_wait_candidate_remains_in_top_watchlist(self):
        item = self.service([self.radar(setup_state="WAIT")]).scan(limit=3)[0]
        assert item["setup_state"] == "WAIT" and item["signal_state"] == "WAIT" and item["selection_role"] == "TOP_WATCHLIST"
        assert item["pipeline_version"] == "1.4" and item["opportunity_score"] == item["session_rank_score"] and item["setup_score"] == 0.0
        assert item["futures_confirmation"] == "NOT_APPLICABLE" and item["futures_confirmation_status"] == "MAPPING_ONLY" and item["rank"] == 1
        assert item["futures_ticker"] == "" and item["futures_selection_reason"] == "WAITING_FOR_CANONICAL_SPOT_READINESS"

    def test_watch_with_active_long_trigger_requires_two_observations(self):
        service = self.service([self.radar(setup_state="WATCH", direction="LONG", spot_price=300.0, entry_trigger=299.0)])
        first = service.scan(limit=3)[0]
        second = service.scan(limit=3)[0]
        assert first["trigger_active"] is True and first["signal_state"] == "ARMED"
        assert first["futures_ticker"] == "" and first["futures_selection_reason"] == "WAITING_FOR_CANONICAL_SPOT_READINESS"
        assert second["trigger_active"] is True and second["signal_state"] == "READY"
        assert second["stability_observations"] == 2 and second["stability_required"] == 2
        assert second["futures_ticker"] == "SRU6"

    def test_watch_with_unreached_long_trigger_is_armed(self):
        item = self.service([self.radar(setup_state="WATCH", direction="LONG", spot_price=298.5, entry_trigger=299.0)]).scan(limit=3)[0]
        assert item["trigger_present"] is True and item["trigger_active"] is False and item["signal_state"] == "ARMED"
        assert "waiting for directional activation" in item["signal_state_reason"]

    def test_watch_with_unreached_short_trigger_is_armed(self):
        item = self.service([self.radar(setup_state="WATCH", direction="SHORT", spot_price=300.0, entry_trigger=299.0, rs=-0.8)]).scan(limit=3)[0]
        assert item["trigger_present"] is True and item["trigger_active"] is False and item["signal_state"] == "ARMED"

    def test_watch_with_active_short_trigger_requires_two_observations(self):
        service = self.service([self.radar(setup_state="WATCH", direction="SHORT", spot_price=298.5, entry_trigger=299.0, rs=-0.8)])
        first = service.scan(limit=3)[0]
        second = service.scan(limit=3)[0]
        assert first["trigger_active"] is True and first["signal_state"] == "ARMED"
        assert first["futures_ticker"] == ""
        assert second["trigger_active"] is True and second["signal_state"] == "READY"
        assert second["futures_ticker"] == "SRU6"

    def test_ready_candidate_remains_ready(self):
        service = self.service([self.radar(setup_state="READY")])
        first = service.scan(limit=3)[0]
        second = service.scan(limit=3)[0]
        assert first["setup_state"] == "READY" and first["signal_state"] == "ARMED"
        assert first["futures_ticker"] == "" and first["futures_selection_reason"] == "WAITING_FOR_CANONICAL_SPOT_READINESS"
        assert second["signal_state"] == "READY" and second["setup_score"] == 70.0 and second["futures_ticker"] == "SRU6"

    def test_confirmed_spot_setup_becomes_confirmed_without_futures_confirmation(self):
        item = self.service([self.radar(setup_state="CONFIRMED")]).scan(limit=3)[0]
        assert item["setup_state"] == "CONFIRMED" and item["signal_state"] == "CONFIRMED" and item["futures_confirmation"] == "NOT_APPLICABLE"
        assert item["futures_ticker"] == "SRU6"

    def test_active_trigger_does_not_churn_after_ready_on_price_retreat(self):
        service = self.service([self.radar(setup_state="WATCH", spot_price=300.0, entry_trigger=299.0)])
        assert service.scan(limit=3)[0]["signal_state"] == "ARMED"
        assert service.scan(limit=3)[0]["signal_state"] == "READY"
        item = service.scan(limit=3)[0]
        assert item["trigger_active"] is True and item["signal_state"] == "READY"
        assert item["futures_ticker"] == "SRU6"

    def test_top_limit_is_three(self):
        radars = [self.radar("A1U6", "SBER", score=90, spot_session_activity_ratio=3.0), self.radar("B1U6", "LKOH", score=85, spot_session_activity_ratio=2.0), self.radar("C1U6", "GAZP", score=80, spot_session_activity_ratio=1.5), self.radar("D1U6", "YDEX", score=75, spot_session_activity_ratio=1.0)]
        candidates = self.service(radars).scan(limit=3)
        assert len(candidates) == 3 and [item["rank"] for item in candidates] == [1, 2, 3]

    def test_event_risk_is_still_rejected_upstream(self):
        radar = self.radar(); radar["moex_event_risk"] = True
        assert self.service([radar]).scan(limit=3) == []

    def test_rs_direction_mismatch_is_still_rejected_upstream(self):
        radar = self.radar(direction="LONG", rs=-0.3)
        assert self.service([radar]).scan(limit=3) == []

    def test_missing_m5_setup_data_is_still_rejected_upstream(self):
        radar = self.radar(); radar["setup_phase"] = "NO_SESSION_CANDLES"
        assert self.service([radar]).scan(limit=3) == []

    def test_diagnostics_are_attached_without_changing_selection(self):
        candidates = self.service([self.radar(setup_state="WAIT"), self.radar("B1U6", "LKOH", setup_state="READY")]).scan(limit=2)
        diagnostics = candidates[0]["scan_diagnostics"]
        assert diagnostics["radar_results"] == 2 and diagnostics["candidates"] == 2 and diagnostics["selected"] == 2
        assert diagnostics["ready"] == 1 and diagnostics["confirmed"] == 0 and diagnostics["wait"] == 1

    def test_short_directional_rs_tiebreak_prefers_more_negative_rs(self):
        radars = [self.radar("A1U6", "GAZP", direction="SHORT", rs=-1.0, spot_price=298.0, entry_trigger=299.0), self.radar("B1U6", "ROSN", direction="SHORT", rs=-2.0, spot_price=298.0, entry_trigger=299.0)]
        assert [item["spot_ticker"] for item in self.service(radars).scan(limit=2)] == ["ROSN", "GAZP"]

    def test_long_directional_rs_tiebreak_prefers_more_positive_rs(self):
        radars = [self.radar("A1U6", "GAZP", direction="LONG", rs=1.0, spot_price=300.0, entry_trigger=299.0), self.radar("B1U6", "ROSN", direction="LONG", rs=2.0, spot_price=300.0, entry_trigger=299.0)]
        assert [item["spot_ticker"] for item in self.service(radars).scan(limit=2)] == ["ROSN", "GAZP"]


if __name__ == "__main__":
    test = TestMorningTradingPipelineService()
    for name in dir(test):
        if name.startswith("test_"):
            getattr(test, name)(); print("PASS", name)
    print("ALL TESTS PASSED")
