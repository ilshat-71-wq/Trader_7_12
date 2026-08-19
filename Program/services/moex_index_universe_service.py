"""Dynamic MOEX index constituent universe for the SPOT-first scanner.

The scanner uses the MOEX Russia Index (IMOEX) basket as its equity SPOT
universe. IRUS/IRUS2 are the market-data display aliases for IMOEX/IMOEX2;
they do not represent a second, different constituent basket.

MOEX publishes the current index composition through its public ISS endpoint.
The universe is cached briefly so a normal scan does not repeatedly hit ISS.
"""

import time

from api.request_helper import RequestHelper


class MoexIndexUniverseService:
    """Load and cache the current MOEX Russia Index constituents."""

    VERSION = "0.1"
    INDEX_CODE = "IMOEX"
    DISPLAY_ALIASES = ("IMOEX", "IRUS")
    ISS_URL = "https://iss.moex.com/iss/statistics/engines/stock/markets/index/analytics/IMOEX.json"
    CACHE_SECONDS = 6 * 60 * 60
    TIMEOUT = 5.0
    MAX_RETRIES = 1

    def __init__(self, request_get=None):
        self._request_get = request_get or RequestHelper.get
        self._cache = None
        self._cache_at = 0.0

    @staticmethod
    def _parse_table(table):
        if not isinstance(table, dict):
            return []

        columns = table.get("columns")
        data = table.get("data")
        if not isinstance(columns, list) or not isinstance(data, list):
            return []

        rows = []
        for row in data:
            if not isinstance(row, (list, tuple)):
                continue
            rows.append(dict(zip(columns, row)))
        return rows

    @classmethod
    def _extract_tickers(cls, payload):
        if not isinstance(payload, dict):
            return set()

        # Standard ISS response.
        rows = cls._parse_table(payload.get("analytics"))
        if not rows:
            rows = cls._parse_table(payload.get("tickers"))

        tickers = set()
        for row in rows:
            ticker = str(
                row.get("ticker")
                or row.get("TICKER")
                or row.get("secid")
                or row.get("SECID")
                or ""
            ).strip().upper()
            if ticker:
                tickers.add(ticker)
        return tickers

    def load(self, force=False):
        """Return the current IMOEX constituent tickers.

        A failed refresh never converts into an empty universe when a previous
        successful snapshot exists. This prevents a temporary ISS outage from
        silently stopping the scanner.
        """
        now = time.monotonic()
        if not force and self._cache is not None and now - self._cache_at < self.CACHE_SECONDS:
            return set(self._cache)

        try:
            response = self._request_get(
                self.ISS_URL,
                params={"iss.meta": "off", "limit": 9999},
                timeout=self.TIMEOUT,
                max_retries=self.MAX_RETRIES,
            )
            if getattr(response, "status_code", 0) != 200:
                raise RuntimeError(f"MOEX ISS HTTP {getattr(response, 'status_code', 'unknown')}")
            payload = response.json()
            tickers = self._extract_tickers(payload)
            if not tickers:
                raise RuntimeError("MOEX ISS returned an empty IMOEX composition")
        except Exception as exc:
            print("⚠️ IMOEX universe refresh failed:", type(exc).__name__, str(exc))
            return set(self._cache or set())

        self._cache = set(tickers)
        self._cache_at = now
        print(f"IMOEX UNIVERSE: {len(tickers)} constituents loaded")
        return set(tickers)

    def filter_mappings(self, mappings):
        """Keep only mappings whose SPOT ticker belongs to the current IMOEX basket."""
        if not isinstance(mappings, list):
            return []

        universe = self.load()
        if not universe:
            return []

        filtered = []
        seen = set()
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            if ticker not in universe:
                continue
            key = (
                ticker,
                str(mapping.get("futures_ticker") or "").strip().upper(),
                str(mapping.get("futures_class_code") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            item = dict(mapping)
            item["spot_universe"] = self.INDEX_CODE
            filtered.append(item)
        return filtered
