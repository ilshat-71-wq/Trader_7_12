from services.historical_universe_replay_service import HistoricalUniverseReplayService


class FakeSpotUniverseService:
    def __init__(self, spots): self.spots = spots; self.calls = 0
    def load(self): self.calls += 1; return list(self.spots)


class FakeMappingService:
    def __init__(self, mappings): self.mappings = mappings; self.calls = 0
    def load(self): self.calls += 1; return list(self.mappings)


class FakeHistoryService:
    MOSCOW_TZ = None


class FakeReplayService:
    MOSCOW_TZ = None


class FakeRadarHelper:
    def calculate_daily_trend(self, daily): return {"direction": "LONG", "trend_days": 3}


def spot(ticker, class_code="TQBR", group="MOEX_STOCK"):
    return {"spot_ticker": ticker, "spot_class_code": class_code, "spot_group": group, "spot_universe": "DYNAMIC_SPOT"}


def mapping(ticker, expiry):
    return {"futures_ticker": ticker, "futures_class_code": "SPBFUT", "futures_expiry": expiry, "spot_ticker": "SBER", "spot_class_code": "TQBR"}


def service(spots=None, mappings=None):
    spot_source = FakeSpotUniverseService(spots or [spot("SBER"), spot("BR", "SPOT", "OIL")])
    mapping_source = FakeMappingService(mappings or [mapping("SRU6", "2026-09-18"), mapping("SRZ6", "2026-12-18")])
    obj = HistoricalUniverseReplayService(mapping_service=mapping_source, history_service=FakeHistoryService(), replay_service=FakeReplayService(), radar_helper=FakeRadarHelper(), spot_universe_service=spot_source)
    obj._test_spot_source = spot_source
    obj._test_mapping_source = mapping_source
    return obj


def test_load_spot_universe_uses_independent_source():
    obj = service()
    result = obj.load_spot_universe()
    assert [x["spot_ticker"] for x in result] == ["BR", "SBER"]
    assert obj._test_spot_source.calls == 1
    assert obj._test_mapping_source.calls == 0


def test_spot_universe_deduplicates_and_normalizes():
    obj = service(spots=[spot("sber"), spot("SBER"), {}, None, spot("LKOH")])
    result = obj.load_spot_universe()
    assert [(x["spot_ticker"], x["spot_class_code"]) for x in result] == [("LKOH", "TQBR"), ("SBER", "TQBR")]


def test_futures_mapping_is_post_spot_context_and_expiry_filtered():
    obj = service(mappings=[mapping("SROLD", "2026-08-27"), mapping("SRU6", "2026-09-18"), mapping("SRZ6", "2026-12-18")])
    result = obj.load_mappings_for_date("2026-08-26")
    assert [x["futures_ticker"] for x in result] == ["SRU6", "SRZ6"]
    assert all(x["days_to_expiry"] > obj.MIN_DAYS_TO_EXPIRY for x in result)


def test_confirmation_window_remains_deterministic():
    assert HistoricalUniverseReplayService.confirmation_window("07:15") == "EARLY"
    assert HistoricalUniverseReplayService.confirmation_window("09:59") == "EARLY"
    assert HistoricalUniverseReplayService.confirmation_window("10:00") == "LATE"
    assert HistoricalUniverseReplayService.confirmation_window("13:00") == "LATE"
    assert HistoricalUniverseReplayService.confirmation_window("13:01") == "NONE"
    assert HistoricalUniverseReplayService.confirmation_window(None) == "NONE"


def test_trigger_activation_is_directional():
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "spot_price": 101, "entry_trigger": 100}) is True
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "spot_price": 99.9, "entry_trigger": 100}) is False
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "SHORT", "setup": "BREAKOUT", "setup_state": "READY", "spot_price": 99, "entry_trigger": 100}) is True
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "SHORT", "setup": "BREAKOUT", "setup_state": "READY", "spot_price": 100.1, "entry_trigger": 100}) is False


def test_first_ready_uses_canonical_lifecycle_and_requires_stable_activation():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99},
        {"checkpoint": "08:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.1},
        {"checkpoint": "09:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.2},
    ]
    ready = HistoricalUniverseReplayService._first_ready(replay)
    assert ready["checkpoint"] == "09:00"
    assert ready["signal_state"] == "READY"
    assert ready["trigger_state"] == "ACTIVE"
    assert ready["stability_observations"] == 2


def test_first_ready_does_not_promote_single_active_observation():
    replay = [
        {"checkpoint": "08:00", "direction": "SHORT", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.5},
        {"checkpoint": "08:30", "direction": "SHORT", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99.8},
    ]
    assert HistoricalUniverseReplayService._first_ready(replay) is None


def test_canonical_historical_lifecycle_marks_armed_before_activation():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "PULLBACK", "setup_state": "WATCH", "entry_trigger": 100, "spot_price": 99},
    ]
    item = HistoricalUniverseReplayService._canonical_lifecycle(replay)[0]
    assert item["signal_state"] == "ARMED"
    assert item["trigger_state"] == "ARMED"
    assert item["trigger_active"] is False
    assert item["stability_observations"] == 0
    assert item["stability_required"] == 2


def test_historical_stability_gate_matches_live_boundary():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99.8},
        {"checkpoint": "08:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.2},
        {"checkpoint": "09:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.4},
    ]
    result = HistoricalUniverseReplayService._canonical_lifecycle(replay)
    assert [item["signal_state"] for item in result] == ["ARMED", "ARMED", "READY"]
    assert [item["stability_observations"] for item in result] == [0, 1, 2]
    assert result[1]["trigger_crossed"] is True
    assert result[2]["trigger_crossed"] is False


def test_historical_stability_counter_resets_on_trigger_loss():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.2},
        {"checkpoint": "08:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99.8},
        {"checkpoint": "09:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.3},
        {"checkpoint": "09:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.4},
    ]
    result = HistoricalUniverseReplayService._canonical_lifecycle(replay)
    assert [item["stability_observations"] for item in result] == [1, 0, 1, 2]
    assert [item["signal_state"] for item in result] == ["ARMED", "ARMED", "ARMED", "READY"]


def test_canonical_historical_lifecycle_is_monotonic_across_checkpoints():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "WATCH", "entry_trigger": 100, "spot_price": 99},
        {"checkpoint": "08:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.2},
        {"checkpoint": "09:00", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.3},
        {"checkpoint": "09:30", "direction": "LONG", "setup": "BREAKOUT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99.8},
    ]
    result = HistoricalUniverseReplayService._canonical_lifecycle(replay)
    assert [item["signal_state"] for item in result] == ["ARMED", "ARMED", "READY", "READY"]
    assert result[1]["trigger_active"] is True
    assert result[3]["trigger_active"] is False


def test_canonical_historical_invalidation_is_terminal_without_new_setup():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup": "PULLBACK", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.2, "invalidation_level": 98},
        {"checkpoint": "08:30", "direction": "LONG", "setup": "PULLBACK", "setup_state": "READY", "entry_trigger": 100, "spot_price": 97.5, "invalidation_level": 98},
        {"checkpoint": "09:00", "direction": "LONG", "setup": "PULLBACK", "setup_state": "READY", "entry_trigger": 100, "spot_price": 101, "invalidation_level": 98},
    ]
    result = HistoricalUniverseReplayService._canonical_lifecycle(replay)
    assert result[1]["signal_state"] == "INVALIDATED"
    assert result[2]["signal_state"] == "INVALIDATED"
