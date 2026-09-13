"""Trader_7_12 Pro - independent SPOT universe source.

The SPOT universe is deliberately independent from futures discovery/mapping.
It is safe to use for production or historical SPOT-first screening before
any futures universe, expiry or liquidity lookup is performed.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from api.bcs_api import BCSAPI
from services.bcs_metadata_cache_service import BCSMetadataCacheService


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
    CACHE_SECONDS = BCSMetadataCacheService.CACHE_SECONDS
    MAX_WORKERS = 6

    def __init__(self, api=None):
        self.api = api or BCSAPI()

    def _load_one(self, instrument_type):
        try:
            records, _ = BCSMetadataCacheService.get_instruments(self.api, instrument_type)
            return instrument_type, records
        except Exception as exc:
            print(f"SPOT metadata unavailable: {instrument_type}: {type(exc).__name__}")
            return instrument_type, []

    def _load_sequential_fallback(self, instrument_types):
        """Retry failed metadata kinds sequentially."""
        recovered = {}
        for instrument_type in instrument_types:
            try:
                kind, records = self._load_one(instrument_type)
            except Exception as exc:
                print(f"SPOT sequential fallback failed: {instrument_type}: {type(exc).__name__}")
                continue
            if records:
                recovered[kind] = records
        return recovered

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

    @staticmethod
    def _weekend_flag(record):
        """Read MOEX SECURITIES.WEEKENDSESSION from BCS metadata when exposed."""
        if not isinstance(record, dict):
            return None
        for key in ("WEEKENDSESSION", "weekendSession", "weekend_session", "weekEndSession", "WeekEndSession"):
            if key not in record:
                continue
            value = record.get(key)
            if isinstance(value, bool):
                return value
            text = str(value).strip().upper()
            if text in {"Y", "YES", "TRUE", "1", "T"}:
                return True
            if text in {"N", "NO", "FALSE", "0", "F"}:
                return False
        return None

    def load(self, weekend_session=None):
        """Return normalized SPOT instruments without consulting futures data."""
        if weekend_session is None:
            try:
                from services.market_session_service import MarketSessionService
                weekend_session = MarketSessionService().get_session() == "WEEKEND_SESSION"
            except Exception:
                weekend_session = False

        if not getattr(self.api, "access_token", None):
            if not self.api.authorize():
                return []

        loaded_by_kind = {}
        with ThreadPoolExecutor(max_workers=min(self.MAX_WORKERS, len(self.INSTRUMENT_TYPES)), thread_name_prefix="spot-universe") as executor:
            pending = [executor.submit(self._load_one, kind) for kind in self.INSTRUMENT_TYPES]
            for future in as_completed(pending):
                try:
                    kind, items = future.result()
                except Exception as exc:
                    print(f"SPOT metadata worker failed: {type(exc).__name__}")
                    continue
                loaded_by_kind[kind] = items if isinstance(items, list) else []

        failed_kinds = [kind for kind in self.INSTRUMENT_TYPES if not loaded_by_kind.get(kind)]
        if failed_kinds:
            loaded_by_kind.update(self._load_sequential_fallback(failed_kinds))

        records = []
        for kind, items in loaded_by_kind.items():
            for item in items:
                if not isinstance(item, dict):
                    continue
                ticker = str(item.get("ticker") or item.get("secCode") or item.get("securityCode") or "").strip().upper()
                class_code = self._class_code(item)
                if not ticker or not class_code:
                    continue
                weekend_flag = self._weekend_flag(item) if kind == "STOCK" else None
                if weekend_session and kind == "STOCK" and weekend_flag is False:
                    continue
                normalized = {
                    "spot_ticker": ticker,
                    "spot_class_code": class_code,
                    "spot_group": self._group(kind, item),
                    "spot_universe": "DYNAMIC_SPOT",
                    "spot_instrument_type": kind,
                }
                if weekend_flag is not None:
                    normalized["weekend_session"] = weekend_flag
                records.append(normalized)

        unique = {}
        for item in records:
            unique[(item["spot_ticker"], item["spot_class_code"])] = item
        return sorted(unique.values(), key=lambda item: (item["spot_ticker"], item["spot_class_code"]))
