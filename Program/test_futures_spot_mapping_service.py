from services.futures_spot_mapping_service import FuturesSpotMappingService


class FakeAPI:
    def __init__(self, futures, spots):
        self.futures = futures
        self.spots = spots

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        if instrument_type == "FUTURES":
            return self.futures
        if instrument_type in {"STOCK", "CURRENCY", "GOODS", "COMMODITY", "COMMODITIES", "METALS", "INDICES"}:
            return self.spots
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
        FakeUniverse([{
            "ticker": "SRU6",
            "classCode": "SPBFUT",
            "expiry": "2026-09-01",
            "underlyingTicker": "SBER",
        }]),
    )
    result = service.map_futures(
        service.futures_universe_service.futures,
        [{"ticker": "SBER", "shortName": "Сбербанк", "classCode": "TQBR"}],
    )
    assert len(result) == 1
    assert result[0]["futures_ticker"] == "SRU6"
    assert result[0]["spot_ticker"] == "SBER"
    assert result[0]["mapping_method"] == "BCS_UNDERLYING"


def test_bmu6_maps_to_brent1026_from_exchange_underlying_metadata():
    """Canonical regression: BMU6 must use BRENT1026 as its SPOT source."""
    service = FuturesSpotMappingService(
        FakeAPI([], []),
        FakeUniverse([{
            "ticker": "BMU6",
            "classCode": "SPBFUT",
            "expiry": "2026-09-01",
            "baseAssetSecuritySecCode": "BRENT1026",
            "baseAssetSecurityClassCode": "SPOT",
            "baseAssetSecurity": {"ticker": "BRENT1026", "classCode": "SPOT"},
        }]),
    )
    result = service.map_futures(
        service.futures_universe_service.futures,
        [{
            "ticker": "BRENT1026",
            "shortName": "Brent Crude Oil 1026",
            "classCode": "SPOT",
            "type": "COMMODITY",
        }],
    )
    assert result == []


def test_nested_underlying_metadata_is_supported():
    service = FuturesSpotMappingService(
        FakeAPI([], []),
        FakeUniverse([{
            "ticker": "SRU6",
            "classCode": "SPBFUT",
            "expiry": "2026-09-01",
            "baseAssetSecurity": {"secCode": "SBER", "classCode": "TQBR"},
        }]),
    )
    result = service.map_futures(
        service.futures_universe_service.futures,
        [{"ticker": "SBER", "shortName": "Сбербанк", "classCode": "TQBR"}],
    )
    assert len(result) == 1
    assert result[0]["spot_ticker"] == "SBER"
    assert result[0]["spot_class_code"] == "TQBR"
    assert result[0]["mapping_method"] == "BCS_UNDERLYING"


def test_unique_spot_metadata_mapping():
    service = FuturesSpotMappingService(
        FakeAPI([], []),
        FakeUniverse([{
            "ticker": "LKU6",
            "classCode": "SPBFUT",
            "expiry": "2026-09-01",
            "shortName": "LKOH futures",
        }]),
    )
    result = service.map_futures(
        service.futures_universe_service.futures,
        [
            {"ticker": "LKOH", "shortName": "LKOH", "classCode": "TQBR"},
            {"ticker": "SBER", "shortName": "SBER", "classCode": "TQBR"},
        ],
    )
    assert len(result) == 1
    assert result[0]["spot_ticker"] == "LKOH"
    assert result[0]["mapping_method"] == "SPOT_METADATA"


def test_ambiguous_mapping_is_rejected():
    service = FuturesSpotMappingService(FakeAPI([], []))
    futures = [{"ticker": "TESTU6", "classCode": "SPBFUT", "expiry": "2026-09-01", "shortName": "TEST futures"}]
    spots = [{"ticker": "AAA", "shortName": "TEST"}, {"ticker": "BBB", "shortName": "TEST"}]
    assert service.map_futures(futures, spots) == []


def test_explicit_metadata_wins_over_name_guess():
    service = FuturesSpotMappingService(FakeAPI([], []))
    futures = [{
        "ticker": "BMU6",
        "classCode": "SPBFUT",
        "expiry": "2026-09-01",
        "baseAssetSecuritySecCode": "BRENT1026",
        "shortName": "Brent futures",
    }]
    spots = [
        {"ticker": "BRENT1026", "shortName": "Brent Crude Oil 1026", "classCode": "SPOT"},
        {"ticker": "BRN", "shortName": "Brent", "classCode": "SPOT"},
    ]
    result = service.map_futures(futures, spots)
    assert len(result) == 1
    assert result[0]["spot_ticker"] == "BRENT1026"
    assert result[0]["mapping_method"] == "BCS_UNDERLYING"


def test_load_authorizes_once_and_maps_dynamic_universe():
    api = FakeAPI(
        [{"ticker": "SRU6", "classCode": "SPBFUT", "expiry": "2026-09-01", "shortName": "SBER futures"}],
        [{"ticker": "SBER", "shortName": "SBER", "classCode": "TQBR"}],
    )
    service = FuturesSpotMappingService(api)
    service.futures_universe_service = FakeUniverse(
        [{"ticker": "SRU6", "classCode": "SPBFUT", "expiry": "2026-09-01", "shortName": "SBER futures"}]
    )
    result = service.load()
    assert len(result) == 1
    assert result[0]["spot_ticker"] == "SBER"
