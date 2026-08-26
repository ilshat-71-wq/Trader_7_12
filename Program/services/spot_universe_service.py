"""Trader_7_12 Pro - independent SPOT universe source.

The SPOT universe is deliberately independent from futures discovery/mapping.
It is safe to use for production or historical SPOT-first screening before
any futures universe, expiry or liquidity lookup is performed.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from api.bcs_api import BCSAPI


class SpotUniverseService:
    """Load and normalize the dynamic SPOT universe directly from BCS metadata."""

    INSTRUMENT_TYPES = (
        "STOCK",
        "CURRENCY",
        "GOODS",
        "COMMODITY",
        "COMMODITIES",
        "METALS",
        "INDICES",
    )
    CACHE_SECONDS = 300
    MAX_WORKERS = 2
    _cache = {}
    _cache_at = {}

    def __init__(self, api=None):
        self.api = api or BCSAPI()

    @classmethod
    def _cached(cls, instrument_type):
        records = cls._cache.get(instrument_type)
        if records is not None and time.monotonic() - cls._cache_at.get(instrument_type, 0.0) < cls.CACHE_SECONDS:
            return list(records)
        return None

    @classmethod
    def _store(cls, instrument_type, records):
        cls._cache[instrument_type] = list(records)
        cls._cache_at[instrument_type] = time.monotonic()

    @staticmethod
    def _class_code(item):
        boards = item.get("boards") or []
        if isinstance(boards, list):
            moex = []
            for board in boards:
                if not isinstance(board, dict):
                    continue
                if str(board.get("exchange") or "").strip().upper() == "MOEX":
                    code = str(board.get("classCode") or board.get("class_code") or "").strip()
                    if code:
                        moex.append(code)
            if "TQBR" in moex:
                return "TQBR"
            if moex:
                return moex[0]
            for board in boards:
                if isinstance(board, dict):
                    code = str(board.get("classCode") or board.get("class_code") or "").strip()
                    if code:
                        return code
        return str(item.get("classCode") or item.get("class_code") or "").strip()

    @staticmethod
    def _group(instrument_type, record):
        explicit = str(record.get("spot_group") or record.get("group") or "").strip()
        if explicit:
            return explicit
        kind = str(instrument_type or "").upper()
        if kind == "STOCK":
            return "MOEX_STOCK"
        if kind == "CURRENCY":
            return "MOEX_CURRENCY"
        if kind in {"GOODS", "COMMODITY", "COMMODITIES", "METALS"}:
            return "MARKET_DRIVER"
        if kind == "INDICES":
            return "MARKET_INDEX"
        return "SPOT"

    def _load_one(self, instrument_type):
        cached = self._cached(instrument_type)
        if cached is not None:
            return instrument_type, cached
        try:
            records = self.api.get_instruments(instrument_type)
        except Exception as exc:
            print(f"SPOT metadata unavailable: {instrument_type}: {type(exc).__name__}")
            return instrument_type, []
        if not isinstance(records, list):
            records = []
        self._store(instrument_type, records)
        return instrument_type, records

    def load(self):
        """Return normalized SPOT instruments without consulting futures data."""
        if not getattr(self.api, "access_token", None):
            if not self.api.authorize():
                return []

        records = []
        with ThreadPoolExecutor(max_workers=min(self.MAX_WORKERS, len(self.INSTRUMENT_TYPES)), thread_name_prefix="spot-universe") as executor:
            pending = [executor.submit(self._load_one, kind) for kind in self.INSTRUMENT_TYPES]
            for future in as_completed(pending):
                try:
                    kind, items = future.result()
                except Exception as exc:
                    print(f"SPOT metadata worker failed: {type(exc).__name__}")
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    ticker = str(item.get("ticker") or item.get("secCode") or item.get("securityCode") or "").strip().upper()
                    class_code = self._class_code(item)
                    if not ticker or not class_code:
                        continue
                    records.append({
                        "spot_ticker": ticker,
                        "spot_class_code": class_code,
                        "spot_group": self._group(kind, item),
                        "spot_universe": "DYNAMIC_SPOT",
                        "spot_instrument_type": kind,
                    })

        unique = {}
        for item in records:
            unique[(item["spot_ticker"], item["spot_class_code"])] = item
        return sorted(unique.values(), key=lambda item: (item["spot_ticker"], item["spot_class_code"]))
