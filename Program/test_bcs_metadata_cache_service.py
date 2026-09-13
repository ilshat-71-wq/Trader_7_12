import threading
import time

from services.bcs_metadata_cache_service import BCSMetadataCacheService


class SlowMetadataAPI:
    def __init__(self):
        self.calls = 0
        self._lock = threading.Lock()

    def get_instruments(self, instrument_type):
        with self._lock:
            self.calls += 1
        time.sleep(0.05)
        return [{"ticker": "SBER", "classCode": "TQBR"}]

    def get_instruments_by_tickers(self, tickers):
        with self._lock:
            self.calls += 1
        time.sleep(0.05)
        return [{
            "ticker": "SBER",
            "_underlying_bcs_class_code": "TQBR",
            "_underlying_mapping_source": "BCS_BY_TYPE_METADATA",
        }]


def test_concurrent_by_type_miss_is_single_request():
    BCSMetadataCacheService.clear()
    api = SlowMetadataAPI()
    results = []

    def worker():
        results.append(BCSMetadataCacheService.get_instruments(api, "STOCK"))

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert api.calls == 1
    assert len(results) == 6
    assert all(result[0][0]["ticker"] == "SBER" for result in results)


def test_concurrent_ticker_miss_is_single_request_and_keeps_fallback_class():
    BCSMetadataCacheService.clear()
    api = SlowMetadataAPI()
    results = []

    def worker():
        results.append(BCSMetadataCacheService.get_instruments_by_tickers(api, ["SBER"]))

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert api.calls == 1
    assert len(results) == 6
    assert all(result[0][0]["_underlying_bcs_class_code"] == "TQBR" for result in results)
