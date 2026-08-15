from services.historical_universe_replay_service import HistoricalUniverseReplayService


class FakeHistoryService:
    MOSCOW_TZ = None


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
