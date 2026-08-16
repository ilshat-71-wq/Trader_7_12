from services.historical_universe_replay_service import HistoricalUniverseReplayService


class FakeHistoryService:
    MOSCOW_TZ = None


class FakeMappingService:
    def __init__(self, mappings):
        self.mappings = mappings

    def load(self):
        return list(self.mappings)


class TestService(HistoricalUniverseReplayService):
    def __init__(self, liquidity_by_ticker):
        self.liquidity_by_ticker = liquidity_by_ticker

    def load_daily_candles(self, ticker, class_code, trading_date):
        return [
            {"close": self.liquidity_by_ticker[ticker], "volume": 1},
        ]


def candidate(ticker, expiry):
    return {
        "futures_ticker": ticker,
        "futures_class_code": "SPBFUT",
        "futures_expiry": expiry,
        "spot_ticker": "OZON",
        "spot_class_code": "SPBXM",
    }


def test_selects_most_liquid_remaining_contract():
    service = TestService({"ONU6": 100, "ONZ6": 250})
    candidates = [
        candidate("ONU6", "2026-09-18"),
        candidate("ONZ6", "2026-12-18"),
    ]

    selected = service.select_futures_for_spot(candidates, "2026-08-14")

    assert selected["futures_ticker"] == "ONZ6"
    assert selected["futures_average_daily_money"] == 250.0


def test_skips_contract_with_three_days_to_expiry_and_uses_next():
    service = TestService({"ONU6": 1000, "ONZ6": 250})
    candidates = [
        candidate("ONU6", "2026-08-17"),
        candidate("ONZ6", "2026-09-18"),
    ]

    selected = service.select_futures_for_spot(candidates, "2026-08-14")

    assert selected["futures_ticker"] == "ONZ6"


def test_skips_contract_with_two_days_to_expiry():
    service = TestService({"ONU6": 1000, "ONZ6": 250})
    candidates = [
        candidate("ONU6", "2026-08-16"),
        candidate("ONZ6", "2026-09-18"),
    ]

    selected = service.select_futures_for_spot(candidates, "2026-08-14")

    assert selected["futures_ticker"] == "ONZ6"


def test_expired_nearest_contract_is_removed_before_taking_two_nearest():
    mappings = [
        candidate("ONU6", "2026-08-17"),
        candidate("ONZ6", "2026-09-18"),
        candidate("ONF7", "2026-12-18"),
    ]
    service = HistoricalUniverseReplayService(
        mapping_service=FakeMappingService(mappings),
        history_service=FakeHistoryService(),
        replay_service=None,
    )

    selected = service.load_mappings_for_date("2026-08-14")

    tickers = [item["futures_ticker"] for item in selected]
    assert tickers == ["ONZ6", "ONF7"]
    assert "ONU6" not in tickers

def test_candidate_rank_prefers_earlier_confirmation_time():
    service = HistoricalUniverseReplayService.__new__(HistoricalUniverseReplayService)

    early = {
        "confirmation_time": "07:30",
        "ready_time": "07:15",
        "futures_confirmation": {"score": 90},
        "candidate": {"futures_average_daily_money": 100},
    }
    late = {
        "confirmation_time": "13:00",
        "ready_time": "07:15",
        "futures_confirmation": {"score": 90},
        "candidate": {"futures_average_daily_money": 100},
    }

    assert service._candidate_rank(early) > service._candidate_rank(late)


def test_candidate_rank_prefers_earlier_ready_time_when_confirmation_matches():
    service = HistoricalUniverseReplayService.__new__(HistoricalUniverseReplayService)

    early = {
        "confirmation_time": "08:00",
        "ready_time": "07:15",
        "futures_confirmation": {"score": 90},
        "candidate": {"futures_average_daily_money": 100},
    }
    late = {
        "confirmation_time": "08:00",
        "ready_time": "09:00",
        "futures_confirmation": {"score": 90},
        "candidate": {"futures_average_daily_money": 100},
    }

    assert service._candidate_rank(early) > service._candidate_rank(late)

def test_confirmation_window_classification():
    assert HistoricalUniverseReplayService.confirmation_window("07:15") == "EARLY"
    assert HistoricalUniverseReplayService.confirmation_window("09:59") == "EARLY"
    assert HistoricalUniverseReplayService.confirmation_window("10:00") == "LATE"
    assert HistoricalUniverseReplayService.confirmation_window("12:59") == "LATE"
    assert HistoricalUniverseReplayService.confirmation_window("13:00") == "LATE"
    assert HistoricalUniverseReplayService.confirmation_window("13:01") == "NONE"
    assert HistoricalUniverseReplayService.confirmation_window(None) == "NONE"


def test_candidate_rank_prefers_early_confirmation_over_late():
    service = HistoricalUniverseReplayService.__new__(HistoricalUniverseReplayService)

    early = {
        "confirmation_time": "07:30",
        "ready_time": "07:15",
        "futures_confirmation": {"score": 80},
        "candidate": {"futures_average_daily_money": 100},
    }
    late = {
        "confirmation_time": "12:00",
        "ready_time": "08:00",
        "futures_confirmation": {"score": 100},
        "candidate": {"futures_average_daily_money": 500},
    }

    assert service._candidate_rank(early) > service._candidate_rank(late)

