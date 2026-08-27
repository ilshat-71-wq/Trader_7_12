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
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "LONG", "spot_price": 101, "entry_trigger": 100}) is True
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "LONG", "spot_price": 99.9, "entry_trigger": 100}) is False
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "SHORT", "spot_price": 99, "entry_trigger": 100}) is True
    assert HistoricalUniverseReplayService._spot_trigger_active({"direction": "SHORT", "spot_price": 100.1, "entry_trigger": 100}) is False


def test_first_ready_requires_active_trigger():
    replay = [
        {"checkpoint": "08:00", "direction": "LONG", "setup_state": "READY", "entry_trigger": 100, "spot_price": 99},
        {"checkpoint": "08:30", "direction": "LONG", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.1},
    ]
    ready = HistoricalUniverseReplayService._first_ready(replay)
    assert ready["checkpoint"] == "08:30"


def test_first_ready_does_not_promote_unreached_ready_state():
    replay = [
        {"checkpoint": "08:00", "direction": "SHORT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.5},
        {"checkpoint": "08:30", "direction": "SHORT", "setup_state": "READY", "entry_trigger": 100, "spot_price": 100.1},
    ]
    assert HistoricalUniverseReplayService._first_ready(replay) is None
