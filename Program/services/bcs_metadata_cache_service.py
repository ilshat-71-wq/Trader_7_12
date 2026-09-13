"""Shared read-only BCS metadata cache.

Metadata is immutable enough for a short process-local TTL. The cache is
shared by scanner services so SPOT universe discovery, BASE lookup and
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

    @staticmethod
    def _lookup_key(value):
        value = str(value or "").strip().upper()
        if not value:
            return ""
        value = value.replace("/", "").replace("-", "").replace("_", "")
        for suffix in ("TOM", "F"):
            if value.endswith(suffix) and len(value) > len(suffix):
                value = value[:-len(suffix)]
                break
        return value

    @classmethod
    def _record_aliases(cls, record):
        if not isinstance(record, dict):
            return set()
        fields = (
            "ticker", "secCode", "securityCode", "baseAssetTicker", "base_asset_ticker",
            "underlyingAsset", "underlying_asset", "underlying", "underlyingTicker",
            "underlying_ticker", "underlyingSecCode", "underlying_sec_code", "assetCode",
            "asset_code", "baseAsset", "base_asset", "baseTicker", "base_ticker",
            "shortCode", "short_code",
        )
        aliases = set()
        for field in fields:
            value = record.get(field)
            if value:
                key = cls._lookup_key(value)
                if key:
                    aliases.add(key)
        if "IMOEX" in aliases:
            aliases.update({"MIX", "MXI", "IMOEXF", "MX", "MM"})
        if "RTS" in aliases:
            aliases.update({"RTSM", "RI", "RM"})
        if "RVI" in aliases:
            aliases.add("VI")
        return aliases

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
        """Resolve real BCS metadata, reusing any already-loaded type catalog first."""
        normalized = tuple(sorted({str(x or "").strip().upper() for x in tickers if str(x or "").strip()}))
        if not normalized:
            return [], True

        # Exact batch cache is the fastest path.
        with cls._lock:
            entry = cls._by_ticker_batch.get(normalized)
            if cls._fresh(entry):
                return list(entry["records"]), True
            cached_type_entries = [
                entry for entry in cls._by_type.values()
                if cls._fresh(entry)
            ]

        wanted = {cls._lookup_key(ticker) for ticker in normalized}
        wanted.discard("")
        cached = []
        seen = set()
        for entry in cached_type_entries:
            for record in entry["records"]:
                aliases = cls._record_aliases(record)
                if not aliases.intersection(wanted):
                    continue
                ticker = str(record.get("ticker") or record.get("secCode") or record.get("securityCode") or "").strip().upper()
                class_code = str(record.get("classCode") or record.get("class_code") or "").strip().upper()
                key = (ticker, class_code)
                if key not in seen:
                    cached.append(record)
                    seen.add(key)

        # If every requested underlying was already represented by a loaded
        # real BCS catalog, do not make another network request.
        matched = set()
        for record in cached:
            matched.update(cls._record_aliases(record).intersection(wanted))
        if matched >= wanted:
            with cls._lock:
                cls._by_ticker_batch[normalized] = {"at": time.monotonic(), "records": list(cached)}
            return list(cached), True

        # Otherwise use the authoritative BCS ticker endpoint. Its existing
        # fallback remains the source of truth for anything not already cached.
        records = api.get_instruments_by_tickers(list(normalized))
        if not isinstance(records, list):
            records = []
        combined = list(cached)
        for record in records:
            ticker = str(record.get("ticker") or record.get("secCode") or record.get("securityCode") or "").strip().upper() if isinstance(record, dict) else ""
            class_code = str(record.get("classCode") or record.get("class_code") or "").strip().upper() if isinstance(record, dict) else ""
            key = (ticker, class_code)
            if key not in seen:
                combined.append(record)
                seen.add(key)
        with cls._lock:
            cls._by_ticker_batch[normalized] = {"at": time.monotonic(), "records": list(combined)}
        return list(combined), False

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._by_type.clear()
            cls._by_ticker_batch.clear()
