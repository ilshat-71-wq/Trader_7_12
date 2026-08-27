from services.morning_trading_pipeline_service import MorningTradingPipelineService


class FakeSessionService:
    def __init__(self, session="MORNING"):
        self.session = session

    def get_session_info(self):
        return {
            "timezone": "Europe/Moscow",
            "date": "2026-08-25",
            "time": "08:30:00",
            "session": self.session,
            "label": self.session,
            "market_open": True,
        }


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
    def radar(
        ticker="SRU6",
        spot="SBER",
        score=90.0,
        direction="LONG",
        spot_group="MOEX_STOCK",
        spot_money_volume=200_000_000,
        spot_money_ratio=2.0,
        spot_session_activity_ratio=2.0,
        setup_state="WAIT",
        rs=0.8,
        spot_price=300.0,
        entry_trigger=299.0,
    ):
        return {
            "status": "OK",
            "direction": direction,
            "futures_ticker": ticker,
            "futures_class_code": "SPBFUT",
            "futures_expiry": "2026-09-15",
            "spot_ticker": spot,
            "spot_class_code": "TQBR",
            "spot_price": spot_price,
            "radar_score": score,
            "relative_strength": rs,
            "relative_strength_status": "OK",
            "relative_strength_signal": "STRONGER" if rs > 0 else "WEAKER",
            "setup": "FIRST_PULLBACK" if direction == "LONG" else "FIRST_REBOUND",
            "setup_direction": direction,
            "setup_state": setup_state,
            "setup_quality_score": 70.0 if setup_state != "WAIT" else 0.0,
            "setup_phase": "SETUP_READY" if setup_state != "WAIT" else "SETUP_SCAN",
            "entry_trigger": entry_trigger,
            "previous_high": 305.0,
            "previous_low": 295.0,
            "spot_money_volume": spot_money_volume,
            "spot_money_ratio": spot_money_ratio,
            "spot_session_activity_ratio": spot_session_activity_ratio,
            "spot_money_per_minute": 10_000_000,
            "spot_change_percent": 1.0 if direction == "LONG" else -1.0,
            "spot_group": spot_group,
            "moex_event_risk": False,
        }

    @staticmethod
    def service(radars, session="MORNING"):
        return MorningTradingPipelineService(
            radar_service=FakeRadarService(radars),
            candidate_service=FakeCandidateService(),
            session_service=FakeSessionService(session),
        )

    def test_wait_candidate_remains_in_top_watchlist(self):
        candidates = self.service([self.radar(setup_state="WAIT")]).scan(limit=3)
        assert len(candidates) == 1
        item = candidates[0]
        assert item["setup_state"] == "WAIT"
        assert item["signal_state"] == "WAIT"
        assert item["selection_role"] == "TOP_WATCHLIST"
        assert item["pipeline_version"] == "1.3"
        assert item["opportunity_score"] == item["session_rank_score"]
        assert item["setup_score"] == 0.0
        assert item["futures_confirmation"] == "NOT_APPLICABLE"
        assert item["futures_confirmation_status"] == "MAPPING_ONLY"
        assert item["rank"] == 1

    def test_watch_with_active_long_trigger_becomes_ready(self):
        candidates = self.service([
            self.radar(setup_state="WATCH", direction="LONG", spot_price=300.0, entry_trigger=299.0)
        ]).scan(limit=3)
        item = candidates[0]
        assert item["setup_state"] == "WATCH"
        assert item["trigger_present"] is True
        assert item["trigger_active"] is True
        assert item["signal_state"] == "READY"

    def test_watch_with_unreached_long_trigger_stays_waiting(self):
        candidates = self.service([
            self.radar(setup_state="WATCH", direction="LONG", spot_price=298.5, entry_trigger=299.0)
        ]).scan(limit=3)
        item = candidates[0]
        assert item["trigger_present"] is True
        assert item["trigger_active"] is False
        assert item["signal_state"] == "WAIT"
        assert "waiting for the directional trigger" in item["signal_state_reason"]

    def test_watch_with_unreached_short_trigger_stays_waiting(self):
        candidates = self.service([
            self.radar(setup_state="WATCH", direction="SHORT", spot_price=300.0, entry_trigger=299.0, rs=-0.8)
        ]).scan(limit=3)
        item = candidates[0]
        assert item["trigger_present"] is True
        assert item["trigger_active"] is False
        assert item["signal_state"] == "WAIT"

    def test_watch_with_active_short_trigger_becomes_ready(self):
        candidates = self.service([
            self.radar(setup_state="WATCH", direction="SHORT", spot_price=298.5, entry_trigger=299.0, rs=-0.8)
        ]).scan(limit=3)
        item = candidates[0]
        assert item["trigger_active"] is True
        assert item["signal_state"] == "READY"

    def test_ready_candidate_remains_ready(self):
        candidates = self.service([self.radar(setup_state="READY")]).scan(limit=3)
        assert len(candidates) == 1
        assert candidates[0]["setup_state"] == "READY"
        assert candidates[0]["signal_state"] == "READY"
        assert candidates[0]["setup_score"] == 70.0

    def test_confirmed_spot_setup_becomes_confirmed_without_futures(self):
        candidates = self.service([self.radar(setup_state="CONFIRMED")]).scan(limit=3)
        assert len(candidates) == 1
        assert candidates[0]["setup_state"] == "CONFIRMED"
        assert candidates[0]["signal_state"] == "CONFIRMED"
        assert candidates[0]["futures_confirmation"] == "NOT_APPLICABLE"

    def test_top_limit_is_three(self):
        radars = [
            self.radar("A1U6", "SBER", score=90, spot_session_activity_ratio=3.0),
            self.radar("B1U6", "LKOH", score=85, spot_session_activity_ratio=2.0),
            self.radar("C1U6", "GAZP", score=80, spot_session_activity_ratio=1.5),
            self.radar("D1U6", "YDEX", score=75, spot_session_activity_ratio=1.0),
        ]
        candidates = self.service(radars).scan(limit=3)
        assert len(candidates) == 3
        assert [item["rank"] for item in candidates] == [1, 2, 3]

    def test_event_risk_is_still_rejected_upstream(self):
        radar = self.radar()
        radar["moex_event_risk"] = True
        assert self.service([radar]).scan(limit=3) == []

    def test_rs_direction_mismatch_is_still_rejected_upstream(self):
        radar = self.radar(direction="LONG", rs=-0.3)
        assert self.service([radar]).scan(limit=3) == []

    def test_missing_m5_setup_data_is_still_rejected_upstream(self):
        radar = self.radar()
        radar["setup_phase"] = "NO_SESSION_CANDLES"
        assert self.service([radar]).scan(limit=3) == []

    def test_diagnostics_are_attached_without_changing_selection(self):
        candidates = self.service([
            self.radar(setup_state="WAIT"),
            self.radar("B1U6", "LKOH", setup_state="READY"),
        ]).scan(limit=2)
        diagnostics = candidates[0]["scan_diagnostics"]
        assert diagnostics["radar_results"] == 2
        assert diagnostics["candidates"] == 2
        assert diagnostics["selected"] == 2
        assert diagnostics["ready"] == 1
        assert diagnostics["confirmed"] == 0
        assert diagnostics["wait"] == 1


if __name__ == "__main__":
    test = TestMorningTradingPipelineService()
    for name in dir(test):
        if name.startswith("test_"):
            getattr(test, name)()
            print("PASS", name)
    print("ALL TESTS PASSED")
