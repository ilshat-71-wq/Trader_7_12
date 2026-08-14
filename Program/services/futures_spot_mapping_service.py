"""
Trader_7_12 Pro

Futures -> SPOT Mapping Service

Stage 2 of the Spot-first architecture.

Purpose:
- build a dynamic mapping from eligible futures to their base SPOT asset;
- use BCS instrument metadata when an explicit underlying ticker is present;
- otherwise use conservative matching against the current stock universe;
- reject ambiguous or unmapped contracts instead of guessing;
- keep mapping separate from trading logic.

The service does NOT generate a trade signal and does NOT select a futures
contract for execution. It only answers:

    FUTURES -> BASE SPOT

No fixed seven-instrument universe is used.
"""

import re

from api.bcs_api import BCSAPI
from services.futures_universe_service import FuturesUniverseService


class FuturesSpotMappingService:
    """Build a conservative dynamic Futures -> SPOT mapping."""

    EXPLICIT_SPOT_KEYS = (
        "underlyingTicker",
        "underlying_ticker",
        "underlyingSecurityCode",
        "underlyingSecurity",
        "baseTicker",
        "base_ticker",
        "spotTicker",
        "spot_ticker",
        "underlyingAsset",
        "underlyingAssetTicker",
    )

    def __init__(self, api=None, futures_universe_service=None):
        self.api = api or BCSAPI()
        self.futures_universe_service = (
            futures_universe_service
            or FuturesUniverseService(self.api)
        )

    def load(self):
        """Return only futures for which a unique SPOT mapping is found."""
        if not self.api.authorize():
            return []

        futures = self.futures_universe_service.load(authorize=False)
        stocks = self.api.get_instruments("STOCK")

        if not isinstance(stocks, list):
            return []

        stock_index = self._build_stock_index(stocks)
        result = []

        for future in futures:
            mapping = self._map_future(future, stocks, stock_index)
            if mapping is not None:
                result.append(mapping)

        return result

    def map_futures(self, futures, stocks):
        """Map supplied normalized futures to supplied raw stock metadata."""
        stock_index = self._build_stock_index(stocks)
        result = []

        for future in futures:
            mapping = self._map_future(future, stocks, stock_index)
            if mapping is not None:
                result.append(mapping)

        return result

    def _map_future(self, future, stocks, stock_index):
        if not isinstance(future, dict):
            return None

        ticker = str(future.get("ticker") or "").strip().upper()
        class_code = str(future.get("classCode") or "").strip()
        if not ticker or not class_code:
            return None

        explicit = self._explicit_underlying(future)
        if explicit:
            candidates = stock_index.get(explicit, [])
            if len(candidates) == 1:
                return self._result(future, candidates[0], "EXPLICIT")
            if len(candidates) > 1:
                return None

        text = self._search_text(future)
        matches = self._match_stocks(text, stocks, stock_index)

        if len(matches) != 1:
            return None

        return self._result(future, matches[0], "STOCK_METADATA")

    @classmethod
    def _build_stock_index(cls, stocks):
        index = {}
        for stock in stocks:
            if not isinstance(stock, dict):
                continue

            ticker = str(stock.get("ticker") or "").strip().upper()
            if not ticker:
                continue

            index.setdefault(ticker, []).append(stock)
        return index

    @classmethod
    def _explicit_underlying(cls, future):
        for key in cls.EXPLICIT_SPOT_KEYS:
            value = future.get(key)
            if isinstance(value, dict):
                value = (
                    value.get("ticker")
                    or value.get("securityCode")
                    or value.get("code")
                )
            if value:
                return str(value).strip().upper()
        return ""

    @staticmethod
    def _search_text(future):
        values = (
            future.get("ticker"),
            future.get("name"),
            future.get("displayName"),
            future.get("shortName"),
        )
        return " ".join(
            str(value or "").upper()
            for value in values
        )

    @classmethod
    def _match_stocks(cls, text, stocks, stock_index):
        matches = []

        # First prefer an exact ticker token in the future metadata.
        for ticker, candidates in stock_index.items():
            if len(candidates) != 1:
                continue
            if cls._contains_token(text, ticker):
                matches.append(candidates[0])

        if len(matches) == 1:
            return matches
        if len(matches) > 1:
            return []

        # Then allow a unique exact short-name phrase match. This is useful
        # for metadata such as "SBER futures" when the underlying field is
        # absent. Never accept an ambiguous match.
        for stock in stocks:
            ticker = str(stock.get("ticker") or "").strip().upper()
            short_name = str(
                stock.get("shortName")
                or stock.get("displayName")
                or ""
            ).strip().upper()
            if not ticker or not short_name:
                continue

            if cls._contains_phrase(text, short_name):
                matches.append(stock)

        unique = {}
        for stock in matches:
            ticker = str(stock.get("ticker") or "").strip().upper()
            if ticker:
                unique[ticker] = stock

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
        if not phrase:
            return False
        return phrase in text

    @staticmethod
    def _result(future, stock, method):
        return {
            "futures_ticker": future.get("ticker"),
            "futures_class_code": future.get("classCode"),
            "futures_expiry": future.get("expiry"),
            "spot_ticker": str(stock.get("ticker") or "").strip().upper(),
            "spot_class_code": str(
                stock.get("classCode")
                or "TQBR"
            ).strip(),
            "spot_name": str(
                stock.get("shortName")
                or stock.get("displayName")
                or ""
            ).strip(),
            "mapping_method": method,
        }
