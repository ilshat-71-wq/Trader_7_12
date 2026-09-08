from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from urllib.parse import urlencode

from api.request_helper import RequestHelper


class OpenInterestService:
    """Professional read-only MOEX futures OI analytics."""

    BASE_URL = "https://iss.moex.com/iss/analyticalproducts/futoi/securities"
    VERSION = "1.1.0"
    HISTORY_DAYS = 60
    ZSCORE_WINDOW = 20
    TIMEOUT = 8
    USER_AGENT = "Trader_7_12/1.1"

    REGIMES = {
        "PRICE_UP_OI_UP": "NEW_POSITION_BUILDING_UP",
        "PRICE_UP_OI_DOWN": "SHORT_COVERING",
        "PRICE_DOWN_OI_UP": "NEW_POSITION_BUILDING_DOWN",
        "PRICE_DOWN_OI_DOWN": "LONG_LIQUIDATION",
        "FLAT": "NEUTRAL",
    }

    def __init__(self, http_get=None):
        self._http_get = http_get or self._default_get
        self._history_cache = {}

    @classmethod
    def _default_get(cls, url, timeout=8):
        """Use the application's shared HTTP/TLS layer for MOEX ISS."""
        response = RequestHelper.get(
            url,
            headers={"User-Agent": cls.USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_block(payload, name="futoi"):
        if not isinstance(payload, dict):
            return []
        block = payload.get(name)
        if isinstance(block, dict) and isinstance(block.get("columns"), list) and isinstance(block.get("data"), list):
            columns = [str(x).lower() for x in block["columns"]]
            return [dict(zip(columns, row)) for row in block["data"] if isinstance(row, list)]
        if isinstance(block, list):
            return [x for x in block if isinstance(x, dict)]
        return []

    def _request_all(self, params):
        return self._http_get(f"{self.BASE_URL}.json?{urlencode(params)}", timeout=self.TIMEOUT)

    def _request_root(self, root, start, end, latest=True):
        params = {"from": start, "till": end, "latest": int(bool(latest))}
        return self._http_get(f"{self.BASE_URL}/{root}.json?{urlencode(params)}", timeout=self.TIMEOUT)

    @staticmethod
    def _number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _aggregate_rows(cls, rows):
        if not rows:
            return None
        ticker = str(rows[0].get("ticker") or "").upper()
        long_oi = sum(max(0.0, cls._number(row.get("pos_long"))) for row in rows)
        short_oi = sum(abs(cls._number(row.get("pos_short"))) for row in rows)
        oi = long_oi if long_oi > 0 else short_oi
        if oi <= 0:
            oi = sum(abs(cls._number(row.get("pos"))) for row in rows) / 2.0
        return {"ticker": ticker, "oi": oi, "oi_long": long_oi, "oi_short": short_oi}

    def load_all(self, trading_date: str | date, latest=True):
        if isinstance(trading_date, date):
            trading_date = trading_date.isoformat()
        rows = self._parse_block(self._request_all({"date": trading_date, "latest": int(bool(latest))}))
        grouped = {}
        for row in rows:
            grouped.setdefault(str(row.get("ticker") or "").upper(), []).append(row)
        result = {}
        for ticker, group in grouped.items():
            aggregate = self._aggregate_rows(group)
            if ticker and aggregate:
                result[ticker] = aggregate
        return result

    def load_history(self, root, start, end, latest=True):
        root = str(root).strip().upper()
        start_s = start.isoformat() if isinstance(start, date) else str(start)
        end_s = end.isoformat() if isinstance(end, date) else str(end)
        key = (root, start_s, end_s, bool(latest))
        if key in self._history_cache:
            return list(self._history_cache[key])
        rows = self._parse_block(self._request_root(root, start_s, end_s, latest))
        by_date = {}
        for row in rows:
            day = str(row.get("tradedate") or row.get("date") or "")[:10]
            if day:
                by_date.setdefault(day, []).append(row)
        series = []
        for day, group in sorted(by_date.items()):
            aggregate = self._aggregate_rows(group)
            if aggregate:
                aggregate["date"] = day
                series.append(aggregate)
        self._history_cache[key] = list(series)
        return series

    @staticmethod
    def _pct_changes(values):
        return [(b / a - 1.0) * 100.0 for a, b in zip(values, values[1:]) if a and a > 0]

    @classmethod
    def zscore(cls, value, history):
        values = [float(x) for x in history if isinstance(x, (int, float))]
        if len(values) < 5:
            return None
        sigma = pstdev(values)
        return 0.0 if sigma == 0 else (float(value) - mean(values)) / sigma

    @classmethod
    def classify(cls, price_change_percent, oi_change_percent, volume_percent=None, oi_zscore=None):
        price = cls._number(price_change_percent)
        oi = cls._number(oi_change_percent)
        if abs(price) < 1e-12 and abs(oi) < 1e-12:
            regime = "FLAT"
        elif price > 0 and oi > 0:
            regime = "PRICE_UP_OI_UP"
        elif price > 0 and oi < 0:
            regime = "PRICE_UP_OI_DOWN"
        elif price < 0 and oi > 0:
            regime = "PRICE_DOWN_OI_UP"
        elif price < 0 and oi < 0:
            regime = "PRICE_DOWN_OI_DOWN"
        else:
            regime = "FLAT"
        strength = "NORMAL"
        if oi_zscore is not None:
            z = abs(float(oi_zscore))
            strength = "ANOMALOUS" if z >= 3 else "STRONG" if z >= 2 else "ELEVATED" if z >= 1 else "NORMAL"
        return {
            "oi_regime": cls.REGIMES[regime],
            "oi_regime_code": regime,
            "oi_strength": strength,
            "oi_zscore": None if oi_zscore is None else round(float(oi_zscore), 3),
            "volume_confirmation": None if volume_percent is None else cls._number(volume_percent) > 0,
        }

    def analyze(self, root, price_change_percent, volume_percent=None, as_of=None):
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        root = str(root).upper()
        current = self.load_all(as_of).get(root)
        if not current:
            return {"oi_status": "UNAVAILABLE", "oi_root": root, "oi_service_version": self.VERSION}
        history = self.load_history(root, as_of - timedelta(days=self.HISTORY_DAYS), as_of)
        previous_oi = next((x["oi"] for x in reversed(history) if x.get("date") < as_of.isoformat()), None)
        oi_change = ((current["oi"] / previous_oi) - 1.0) * 100.0 if previous_oi and previous_oi > 0 else None
        changes = self._pct_changes([x["oi"] for x in history])
        z = self.zscore(oi_change, changes[-self.ZSCORE_WINDOW:]) if oi_change is not None else None
        return {
            "oi_status": "AVAILABLE" if oi_change is not None else "CURRENT_ONLY",
            "oi_root": root,
            "oi": current["oi"],
            "oi_change_percent": None if oi_change is None else round(oi_change, 3),
            "oi_history_days": len(history),
            "oi_service_version": self.VERSION,
            **self.classify(price_change_percent, oi_change or 0.0, volume_percent, z),
        }
