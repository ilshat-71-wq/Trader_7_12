"""
Trader_7_12 Pro

Futures -> SPOT Mapping Service

Stage 2 of the Spot-first architecture.

Purpose:
- map the dynamic MOEX futures universe to the corresponding SPOT asset;
- use explicit BCS underlying metadata whenever available;
- support stocks, currencies, commodities and indices instead of a
  stock-only universe;
- reject ambiguous or unmapped contracts instead of guessing.

Performance rules:
- instrument metadata is cached in-process for a short TTL;
- independent SPOT instrument-type requests run concurrently;
- a temporary failure of one type does not block the remaining universe.

There is deliberately NO fixed instrument universe here.

Hard universe rule:
    A futures contract enters the downstream pipeline ONLY when a unique,
    usable SPOT ticker and SPOT class code are available. Unmapped,
    ambiguous, or otherwise incomplete contracts are discarded here before
    any SPOT history, liquidity, radar, or ranking work is performed.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.bcs_api import BCSAPI
from services.futures_universe_service import FuturesUniverseService


class FuturesSpotMappingService:
    """Build a dynamic, conservative Futures -> SPOT mapping."""

    SPOT_INSTRUMENT_TYPES = (
        "STOCK",
        "CURRENCY",
        "GOODS",
        "COMMODITY",
        "COMMODITIES",
        "METALS",
        "INDICES",
    )

    VALID_MAPPING_METHODS = {
        "BCS_UNDERLYING",
        "SPOT_METADATA",
    }

    # Metadata is stable enough to reuse between scans. A fresh process starts
    # empty; subsequent scans avoid repeating the same 7 instrument-list calls.
    INSTRUMENT_CACHE_SECONDS = 300
    MAX_METADATA_WORKERS = 4
    _instrument_cache = {}
    _instrument_cache_at = {}

    EXPLICIT_SPOT_KEYS = (
        "baseAssetSecuritySecCode",
        "baseAssetSecurity",
        "baseAsset",
        "baseAssetFuture",
        "underlyingTicker",
        "underlying_ticker",
        "underlyingSecurityCode",
        "underlyingAssetTicker",
        "spotTicker",
        "spot_ticker",
        "baseTicker",
        "base_ticker",
        "underlyingSecurity",
        "underlyingAsset",
    )

    EXPLICIT_CLASS_KEYS = (
        "baseAssetSecurityClassCode",
        "underlyingClassCode",
        "underlying_class_code",
        "underlyingSecurityClassCode",
        "underlying_security_class_code",
        "spotClassCode",
        "spot_class_code",
        "baseClassCode",
        "base_class_code",
    )

    def __init__(self, api=None, futures_universe_service=None):
        self.api = api or BCSAPI()
        self.futures_universe_service = (
            futures_universe_service
            or FuturesUniverseService(self.api)
        )

    def load(self):
        """Return only futures for which a unique usable SPOT is known."""
        if not self.api.authorize():
            return []

        futures = self.futures_universe_service.load(authorize=False)
        spots = self._load_spot_instruments()

        if not isinstance(futures, list) or not spots:
            return []

        spot_index = self._build_spot_index(spots)
        result = []

        for future in futures:
            mapping = self._map_future(future, spots, spot_index)
            if self._is_valid_mapping(mapping):
                result.append(mapping)

        return result

    def map_futures(self, futures, spots):
        """Map supplied normalized futures to supplied raw SPOT metadata."""
        spot_index = self._build_spot_index(spots)
        result = []

        for future in futures:
            mapping = self._map_future(future, spots, spot_index)
            if self._is_valid_mapping(mapping):
                result.append(mapping)

        return result

    @classmethod
    def _cached_type(cls, instrument_type):
        now = time.monotonic()
        cached = cls._instrument_cache.get(instrument_type)
        cached_at = cls._instrument_cache_at.get(instrument_type, 0.0)
        if cached is not None and now - cached_at < cls.INSTRUMENT_CACHE_SECONDS:
            return list(cached)
        return None

    @classmethod
    def _store_type(cls, instrument_type, records):
        cls._instrument_cache[instrument_type] = list(records)
        cls._instrument_cache_at[instrument_type] = time.monotonic()

    def _load_one_spot_type(self, instrument_type):
        cached = self._cached_type(instrument_type)
        if cached is not None:
            return instrument_type, cached, True

        try:
            records = self.api.get_instruments(instrument_type)
        except Exception as exc:
            print(
                f"⚠️ SPOT metadata skipped: {instrument_type} "
                f"({type(exc).__name__})"
            )
            return instrument_type, [], False

        if not isinstance(records, list):
            records = []

        self._store_type(instrument_type, records)
        return instrument_type, records, False

    def _load_spot_instruments(self):
        """Load SPOT metadata concurrently and reuse it between scans."""
        result = []
        seen = set()

        pending = []
        with ThreadPoolExecutor(
            max_workers=min(self.MAX_METADATA_WORKERS, len(self.SPOT_INSTRUMENT_TYPES)),
            thread_name_prefix="spot-meta",
        ) as executor:
            futures = {
                executor.submit(self._load_one_spot_type, instrument_type): instrument_type
                for instrument_type in self.SPOT_INSTRUMENT_TYPES
            }
            for future in as_completed(futures):
                try:
                    _, records, _ = future.result()
                except Exception as exc:
                    print(
                        "⚠️ SPOT metadata worker failed:",
                        type(exc).__name__
                    )
                    records = []
                pending.extend(records)

        for record in pending:
            if not isinstance(record, dict):
                continue

            ticker = str(record.get("ticker") or "").strip().upper()
            class_code = self._class_code(record)

            if not ticker or not class_code:
                continue

            key = (ticker, class_code)
            if key in seen:
                continue

            seen.add(key)
            result.append(record)

        return result

    @staticmethod
    def _class_code(item):
        boards = item.get("boards") or []
        if isinstance(boards, list):
            for board in boards:
                if not isinstance(board, dict):
                    continue
                value = str(board.get("classCode") or "").strip()
                if value:
                    return value

        return str(item.get("classCode") or "").strip()

    @classmethod
    def _build_spot_index(cls, spots):
        index = {}

        for spot in spots:
            if not isinstance(spot, dict):
                continue

            ticker = str(spot.get("ticker") or "").strip().upper()
            if not ticker:
                continue

            index.setdefault(ticker, []).append(spot)

        return index

    @classmethod
    def _map_future(cls, future, spots, spot_index):
        if not isinstance(future, dict):
            return None

        futures_ticker = str(future.get("ticker") or "").strip().upper()
        futures_class_code = str(future.get("classCode") or "").strip()

        if not futures_ticker or not futures_class_code:
            return None

        explicit = cls._explicit_underlying(future)

        if explicit["ticker"]:
            candidates = spot_index.get(explicit["ticker"], [])

            if explicit["class_code"]:
                candidates = [
                    item for item in candidates
                    if cls._class_code(item) == explicit["class_code"]
                ]

            # An explicit BCS underlying is authoritative. If it cannot be
            # resolved to exactly one usable SPOT, reject the future rather
            # than falling back to name matching and accidentally guessing.
            if len(candidates) != 1:
                return None

            return cls._result(future, candidates[0], "BCS_UNDERLYING")

        text = cls._search_text(future)
        matches = cls._match_spots(text, spots, spot_index)

        if len(matches) != 1:
            return None

        return cls._result(future, matches[0], "SPOT_METADATA")

    @classmethod
    def _explicit_underlying(cls, future):
        """Extract a BCS underlying from scalar or nested metadata objects."""
        ticker = ""
        class_code = ""

        for key in cls.EXPLICIT_SPOT_KEYS:
            value = future.get(key)
            candidate_ticker, candidate_class = cls._extract_underlying_value(value)

            if candidate_ticker:
                ticker = candidate_ticker
                if candidate_class:
                    class_code = candidate_class
                break

        for key in cls.EXPLICIT_CLASS_KEYS:
            value = future.get(key)
            if isinstance(value, dict):
                value = (
                    value.get("classCode")
                    or value.get("class_code")
                    or value.get("code")
                )
            if value:
                class_code = str(value).strip()
                break

        return {"ticker": ticker, "class_code": class_code}

    @staticmethod
    def _extract_underlying_value(value):
        if not value:
            return "", ""

        if isinstance(value, dict):
            ticker = str(
                value.get("ticker")
                or value.get("securityCode")
                or value.get("secCode")
                or value.get("code")
                or value.get("symbol")
                or ""
            ).strip().upper()
            class_code = str(
                value.get("classCode")
                or value.get("class_code")
                or value.get("securityClassCode")
                or ""
            ).strip()
            return ticker, class_code

        return str(value).strip().upper(), ""

    @staticmethod
    def _search_text(future):
        values = (
            future.get("ticker"),
            future.get("name"),
            future.get("displayName"),
            future.get("shortName"),
            future.get("baseAsset"),
            future.get("baseAssetFuture"),
            future.get("baseAssetSecurity"),
        )
        return " ".join(str(value or "").upper() for value in values)

    @classmethod
    def _match_spots(cls, text, spots, spot_index):
        matches = []

        for ticker, candidates in spot_index.items():
            if len(candidates) != 1:
                continue
            if cls._contains_token(text, ticker):
                matches.append(candidates[0])

        if len(matches) == 1:
            return matches
        if len(matches) > 1:
            return []

        for spot in spots:
            short_name = str(
                spot.get("shortName")
                or spot.get("displayName")
                or ""
            ).strip().upper()

            if short_name and cls._contains_phrase(text, short_name):
                matches.append(spot)

        unique = {}
        for spot in matches:
            ticker = str(spot.get("ticker") or "").strip().upper()
            class_code = cls._class_code(spot)
            if ticker and class_code:
                unique[(ticker, class_code)] = spot

        return list(unique.values())

    @staticmethod
    def _contains_token(text, token):
        if not token:
            return False
        return re.search(
            rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])",
            text,
        ) is not None

    @staticmethod
    def _contains_phrase(text, phrase):
        return bool(phrase) and phrase in text

    @classmethod
    def _result(cls, future, spot, method):
        return {
            "futures_ticker": future.get("ticker"),
            "futures_class_code": future.get("classCode"),
            "futures_expiry": future.get("expiry"),
            "spot_ticker": str(spot.get("ticker") or "").strip().upper(),
            "spot_class_code": cls._class_code(spot),
            "spot_name": str(
                spot.get("shortName")
                or spot.get("displayName")
                or ""
            ).strip(),
            "spot_type": str(
                spot.get("type")
                or spot.get("instrumentType")
                or ""
            ).strip().upper(),
            "mapping_method": method,
        }

    @classmethod
    def _is_valid_mapping(cls, mapping):
        """Hard gate for every mapping entering the downstream pipeline."""
        if not isinstance(mapping, dict):
            return False

        futures_ticker = str(mapping.get("futures_ticker") or "").strip()
        futures_class = str(mapping.get("futures_class_code") or "").strip()
        spot_ticker = str(mapping.get("spot_ticker") or "").strip().upper()
        spot_class = str(mapping.get("spot_class_code") or "").strip()
        method = str(mapping.get("mapping_method") or "").strip().upper()

        return bool(
            futures_ticker
            and futures_class
            and spot_ticker
            and spot_class
            and method in cls.VALID_MAPPING_METHODS
        )
