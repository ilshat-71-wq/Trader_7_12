from services.futures_spot_mapping_service import FuturesSpotMappingService


class FakeAPI:
    def __init__(self, futures, stocks):
        self.futures = futures
        self.stocks = stocks

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        if instrument_type == "FUTURES":
            return self.futures
        if instrument_type == "STOCK":
            return self.stocks
        raise AssertionError(f"Unexpected type: {instrument_type}")


class FakeUniverse:
    def __init__(self, futures):
        self.futures = futures

    def load(self, authorize=True):
        assert authorize is False
        return self.futures


def test_explicit_underlying_mapping():
    service = FuturesSpotMappingService(
        FakeAPI([], []),
        FakeUniverse(
            [
                {
                    "ticker": "SRU6",
                    "classCode": "SPBFUT",
                    "expiry": "2026-09-01",
                    "underlyingTicker": "SBER",
                }
            ]
        ),
    )

    result = service.map_futures(
        service.futures_universe_service.futures,
        [
            {
                "ticker": "SBER",
                "shortName": "Сбербанк",
                "classCode": "TQBR",
            }
        ],
    )

    assert len(result) == 1
    assert result[0]["futures_ticker"] == "SRU6"
    assert result[0]["spot_ticker"] == "SBER"
    assert result[0]["mapping_method"] == "EXPLICIT"


def test_unique_stock_metadata_mapping():
    service = FuturesSpotMappingService(
        FakeAPI([], []),
        FakeUniverse(
            [
                {
                    "ticker": "LKU6",
                    "classCode": "SPBFUT",
                    "expiry": "2026-09-01",
                    "shortName": "LKOH futures",
                }
            ]
        ),
    )

    result = service.map_futures(
        service.futures_universe_service.futures,
        [
            {
                "ticker": "LKOH",
                "shortName": "LKOH",
                "classCode": "TQBR",
            },
            {
                "ticker": "SBER",
                "shortName": "SBER",
                "classCode": "TQBR",
            },
        ],
    )

    assert len(result) == 1
    assert result[0]["spot_ticker"] == "LKOH"
    assert result[0]["mapping_method"] == "STOCK_METADATA"


def test_ambiguous_mapping_is_rejected():
    service = FuturesSpotMappingService(FakeAPI([], []))

    futures = [
        {
            "ticker": "TESTU6",
            "classCode": "SPBFUT",
            "expiry": "2026-09-01",
            "shortName": "TEST futures",
        }
    ]

    stocks = [
        {"ticker": "AAA", "shortName": "TEST"},
        {"ticker": "BBB", "shortName": "TEST"},
    ]

    assert service.map_futures(futures, stocks) == []


def test_load_authorizes_once_and_maps_dynamic_universe():
    api = FakeAPI(
        [
            {
                "ticker": "SRU6",
                "classCode": "SPBFUT",
                "expiry": "2026-09-01",
                "shortName": "SBER futures",
            }
        ],
        [
            {
                "ticker": "SBER",
                "shortName": "SBER",
                "classCode": "TQBR",
            }
        ],
    )

    service = FuturesSpotMappingService(api)
    service.futures_universe_service = FakeUniverse(
        [
            {
                "ticker": "SRU6",
                "classCode": "SPBFUT",
                "expiry": "2026-09-01",
                "shortName": "SBER futures",
            }
        ]
    )

    result = service.load()

    assert len(result) == 1
    assert result[0]["spot_ticker"] == "SBER"
