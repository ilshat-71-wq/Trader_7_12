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

There is deliberately NO fixed seven-instrument universe here.
"""

import re

from api.bcs_api import BCSAPI
from services.futures_universe_service import FuturesUniverseService


class FuturesSpotMappingService:
    """Build a dynamic, conservative Futures -> SPOT mapping."""

    SPOT_INSTRUMENT_TYPES = (
        "STOCK",
        "CURRENCY",
        "COMMODITY",
        "INDEX",
    )

    EXPLICIT_SPOT_KEYS = (
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
        """Return every eligible future for which a unique SPOT is known."""
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
            if mapping is not None:
                result.append(mapping)

        return result

    def map_futures(self, futures, spots):
        """Map supplied normalized futures to supplied raw SPOT metadata."""
        spot_index = self._build_spot_index(spots)
        result = []

        for future in futures:
            mapping = self._map_future(future, spots, spot_index)
            if mapping is not None:
                result.append(mapping)

        return result

    def _load_spot_instruments(self):
        """Load supported SPOT types; unavailable types are skipped."""
        result = []
        seen = set()

        for instrument_type in self.SPOT_INSTRUMENT_TYPES:
            try:
                records = self.api.get_instruments(instrument_type)
            except Exception:
                continue

            if not isinstance(records, list):
                continue

            for record in records:
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

            if len(candidates) == 1:
                return cls._result(future, candidates[0], "EXPLICIT")

            if len(candidates) > 1:
                return None

        text = cls._search_text(future)
        matches = cls._match_spots(text, spots, spot_index)

        if len(matches) != 1:
            return None

        return cls._result(future, matches[0], "SPOT_METADATA")

    @classmethod
    def _explicit_underlying(cls, future):
        ticker = ""
        class_code = ""

        for key in cls.EXPLICIT_SPOT_KEYS:
            value = future.get(key)

            if isinstance(value, dict):
                ticker = str(
                    value.get("ticker")
                    or value.get("securityCode")
                    or value.get("code")
                    or ""
                ).strip().upper()
                class_code = str(
                    value.get("classCode")
                    or value.get("class_code")
                    or ""
                ).strip()
            elif value:
                ticker = str(value).strip().upper()

            if ticker:
                break

        for key in cls.EXPLICIT_CLASS_KEYS:
            value = future.get(key)
            if value:
                class_code = str(value).strip()
                break

        return {"ticker": ticker, "class_code": class_code}

    @staticmethod
    def _search_text(future):
        values = (
            future.get("ticker"),
            future.get("name"),
            future.get("displayName"),
            future.get("shortName"),
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
