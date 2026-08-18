"""Offline tests for the scanner's network-request optimization layer."""

from services.futures_spot_mapping_service import FuturesSpotMappingService


class FakeAPI:
    def __init__(self):
        self.calls = []

    def get_instruments(self, instrument_type):
        self.calls.append(instrument_type)
        return [{"ticker": f"TEST_{instrument_type}", "classCode": "TST"}]



def test_spot_metadata_is_cached_between_loads():
    FuturesSpotMappingService._instrument_cache.clear()
    FuturesSpotMappingService._instrument_cache_at.clear()
    api = FakeAPI()
    service = FuturesSpotMappingService(api=api)
    first = service._load_spot_instruments()
    first_call_count = len(api.calls)
    second = service._load_spot_instruments()
    assert first
    assert second
    assert first_call_count == len(FuturesSpotMappingService.SPOT_INSTRUMENT_TYPES)
    assert len(api.calls) == first_call_count



def test_spot_metadata_keeps_all_available_types_after_parallel_load():
    FuturesSpotMappingService._instrument_cache.clear()
    FuturesSpotMappingService._instrument_cache_at.clear()
    api = FakeAPI()
    service = FuturesSpotMappingService(api=api)
    records = service._load_spot_instruments()
    tickers = {item["ticker"] for item in records}
    assert len(tickers) == len(FuturesSpotMappingService.SPOT_INSTRUMENT_TYPES)
    assert set(api.calls) == set(FuturesSpotMappingService.SPOT_INSTRUMENT_TYPES)


if __name__ == "__main__":
    test_spot_metadata_is_cached_between_loads()
    print("PASS test_spot_metadata_is_cached_between_loads")
    test_spot_metadata_keeps_all_available_types_after_parallel_load()
    print("PASS test_spot_metadata_keeps_all_available_types_after_parallel_load")
    print("ALL TESTS PASSED")
