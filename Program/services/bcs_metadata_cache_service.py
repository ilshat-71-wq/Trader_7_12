"""Shared read-only BCS metadata cache.

Metadata is immutable enough for a short process-local TTL. The cache is
shared by all scanner services so SPOT universe discovery, BASE lookup and
futures-underlying mapping do not download the same BCS catalog repeatedly.
Quote/candle data is intentionally not cached here.
"""

from threading import RLock
import time


class BCSMetadataCacheService:
    CACHE_SECONDS = 300
    _lock = RLock()
    _by_type = {}
    _by_ticker_batch = {}

    @classmethod
    def _fresh(cls, entry):
        return entry is not None and time.monotonic() - entry["at"] < cls.CACHE_SECONDS

    @classmethod
    def get_instruments(cls, api, instrument_type):
        key = str(instrument_type or "").strip().upper()
        with cls._lock:
            entry = cls._by_type.get(key)
            if cls._fresh(entry):
                return list(entry["records"]), True
        records = api.get_instruments(instrument_type)
        if not isinstance(records, list):
            records = []
        with cls._lock:
            cls._by_type[key] = {"at": time.monotonic(), "records": list(records)}
        return list(records), False

    @classmethod
    def get_instruments_by_tickers(cls, api, tickers):
        normalized = tuple(sorted({str(x or "").strip().upper() for x in tickers if str(x or "").strip()}))
        if not normalized:
            return [], True
        key = normalized
        with cls._lock:
            entry = cls._by_ticker_batch.get(key)
            if cls._fresh(entry):
                return list(entry["records"]), True
        records = api.get_instruments_by_tickers(list(normalized))
        if not isinstance(records, list):
            records = []
        with cls._lock:
            cls._by_ticker_batch[key] = {"at": time.monotonic(), "records": list(records)}
        return list(records), False

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._by_type.clear()
            cls._by_ticker_batch.clear()
