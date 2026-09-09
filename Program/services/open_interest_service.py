from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from urllib.parse import quote, urlencode

from api.request_helper import RequestHelper


class OpenInterestService:
    """Read-only MOEX futures OI analytics."""

    BASE_URL = "https://iss.moex.com/iss/analyticalproducts/futoi/securities"
    FUTURES_MARKETDATA_URL = "https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities"
    FUTURES_MARKETDATA_ALL_URL = f"{FUTURES_MARKETDATA_URL}.json?iss.only=marketdata"
    VERSION = "1.4.1"
    HISTORY_DAYS = 60
    ZSCORE_WINDOW = 20
    TIMEOUT = 8
    USER_AGENT = "Trader_7_12/1.4"

    MOEX_PREFIX_BY_ROOT = {
        "AF": "AFLT", "AL": "ALRS", "SR": "SBRF", "GZ": "GAZR", "LK": "LKOH",
        "RN": "ROSN", "CH": "CHMF", "NM": "NLMK", "MG": "MAGN", "SZ": "SGZH",
        "RU": "RNFT", "ON": "OZON", "VB": "VTBR", "PH": "PHOR", "PI": "PIKK",
        "RA": "RASP", "LE": "LEAS", "AS": "ASTR", "BS": "BSPB", "BN": "BANE",
        "KM": "KMAZ", "FL": "FLOT", "MV": "MVID", "CM": "CBOM", "FE": "FESH",
        "RT": "RTKM", "SO": "SIBN", "TI": "TCSI", "VK": "VKCO", "PO": "POLY",
        "PZ": "PLZL", "YD": "YDEX", "SS": "SMLT", "PS": "POSI", "SE": "SPBE",
        "RL": "RUAL", "RE": "RSTI", "NA": "QQQ", "MX": "MIX", "MM": "MXI",
        "RI": "RTS", "RM": "RTSM", "VI": "RVI", "SI": "Si", "EU": "Eu",
        "CR": "CNY", "BR": "BR", "GD": "GOLD", "GL": "GL", "NG": "NG",
        "CL": "CL", "WT": "WT", "SV": "SILV", "PD": "PLAT",
    }
    MONTH_CODES = {"H": 3, "M": 6, "U": 9, "Z": 12}

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
        self._all_cache = {}
        self._marketdata_cache = {}
        self._marketdata_all_cache = None

    @classmethod
    def _default_get(cls, url, timeout=8):
        response = RequestHelper.get(url, headers={"User-Agent": cls.USER_AGENT, "Accept": "application/json"}, timeout=timeout)
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
        return self._http_get(f"{self.BASE_URL}/{quote(str(root).upper(), safe='')}.json?{urlencode(params)}", timeout=self.TIMEOUT)

    def _request_marketdata(self, contract_ticker):
        ticker = str(contract_ticker or "").strip().upper()
        if not ticker:
            return None
        if ticker in self._marketdata_cache:
            return self._marketdata_cache[ticker]
        url = f"{self.FUTURES_MARKETDATA_URL}/{quote(ticker, safe='')}.json?iss.only=marketdata"
        try:
            payload = self._http_get(url, timeout=self.TIMEOUT)
        except Exception:
            return None
        rows = self._parse_block(payload, "marketdata")
        row = rows[0] if rows else None
        self._marketdata_cache[ticker] = row
        return row

    def _load_marketdata_all(self):
        if self._marketdata_all_cache is None:
            try:
                payload = self._http_get(self.FUTURES_MARKETDATA_ALL_URL, timeout=self.TIMEOUT)
                self._marketdata_all_cache = self._parse_block(payload, "marketdata")
            except Exception:
                self._marketdata_all_cache = []
        return list(self._marketdata_all_cache)

    @classmethod
    def _marketdata_family(cls, secid):
        """Return the RFUD family by removing a standard futures expiry suffix."""
        secid = str(secid or "").strip().upper()
        if not secid:
            return ""
        if "-" in secid:
            return secid.split("-", 1)[0]
        # Standard MOEX quarterly code: FAMILY + month letter + year digit,
        # e.g. ALU6, ALZ6, SiM7, MXU6, NAU6. This generic rule also covers
        # families that are not in our static reverse map.
        if len(secid) >= 3 and secid[-2] in cls.MONTH_CODES and secid[-1].isdigit():
            return secid[:-2]
        prefixes = {str(value).upper() for value in cls.MOEX_PREFIX_BY_ROOT.values()}
        for prefix in sorted(prefixes, key=len, reverse=True):
            if secid.startswith(prefix) and len(secid) > len(prefix):
                return prefix
        return secid

    @classmethod
    def _marketdata_expiry(cls, secid, as_of=None):
        """Parse RFUD SECID expiry; perpetual/daily contracts have no expiry."""
        secid = str(secid or "").strip().upper()
        if not secid:
            return date.max
        if "-" in secid:
            tail = secid.rsplit("-", 1)[1]
            if "." in tail:
                month_s, year_s = tail.split(".", 1)
                if month_s.isdigit() and year_s.isdigit():
                    try:
                        return date(2000 + int(year_s), int(month_s), 1)
                    except ValueError:
                        pass
        if len(secid) >= 3 and secid[-2] in cls.MONTH_CODES and secid[-1].isdigit():
            return date(2000 + int(secid[-1]), cls.MONTH_CODES[secid[-2]], 1)
        return date.max

    @classmethod
    def _front_marketdata_rows(cls, rows, as_of=None):
        """Select one active, non-zero-OI front contract per MOEX family."""
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        grouped = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            secid = str(row.get("secid") or row.get("ticker") or "").upper()
            family = cls._marketdata_family(secid)
            oi = cls._number(row.get("openposition"))
            if not secid or not family or oi <= 0:
                continue
            expiry = cls._marketdata_expiry(secid, as_of)
            if expiry != date.max and expiry < as_of:
                continue
            grouped.setdefault(family, []).append((expiry, secid, row))
        selected = {}
        for family, candidates in grouped.items():
            candidates.sort(key=lambda item: (item[0], item[1]))
            expiry, secid, row = candidates[0]
            selected[family] = dict(row)
            selected[family]["_moex_family"] = family
            selected[family]["_moex_expiry"] = None if expiry == date.max else expiry.isoformat()
        return selected

    def marketdata_front_contracts(self, as_of=None):
        """Return the current front RFUD contract with OI>0 for each MOEX family."""
        return self._front_marketdata_rows(self._load_marketdata_all(), as_of=as_of)

    def _request_marketdata_family(self, root):
        root = str(root or "").strip().upper()
        if not root:
            return None
        rows = self._load_marketdata_all()
        selected = self._front_marketdata_rows(rows).get(root)
        if selected:
            return selected
        prefix = self.MOEX_PREFIX_BY_ROOT.get(root, root)
        candidates = []
        for row in rows:
            secid = str(row.get("secid") or row.get("ticker") or "").upper()
            if secid == prefix or secid.startswith(prefix + "-"):
                if self._number(row.get("openposition")) > 0:
                    candidates.append(row)
        if not candidates:
            return None
        candidates.sort(key=lambda row: self._marketdata_expiry(row.get("secid") or row.get("ticker")))
        return candidates[0]

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
        oi = (long_oi + short_oi) / 2.0 if long_oi > 0 and short_oi > 0 else sum(abs(cls._number(row.get("pos"))) for row in rows) / 2.0
        return {"ticker": ticker, "oi": oi, "oi_long": long_oi, "oi_short": short_oi}

    def load_all(self, trading_date: str | date, latest=True):
        if isinstance(trading_date, date):
            trading_date = trading_date.isoformat()
        key = (str(trading_date), bool(latest))
        if key in self._all_cache:
            return dict(self._all_cache[key])
        try:
            rows = self._parse_block(self._request_all({"date": trading_date, "latest": int(bool(latest))}))
        except Exception:
            rows = []
        grouped = {}
        for row in rows:
            grouped.setdefault(str(row.get("ticker") or "").upper(), []).append(row)
        result = {}
        for ticker, group in grouped.items():
            aggregate = self._aggregate_rows(group)
            if ticker and aggregate:
                result[ticker] = aggregate
        self._all_cache[key] = dict(result)
        return result

    def load_history(self, root, start, end, latest=True):
        root = str(root).strip().upper()
        start_s = start.isoformat() if isinstance(start, date) else str(start)
        end_s = end.isoformat() if isinstance(end, date) else str(end)
        key = (root, start_s, end_s, bool(latest))
        if key in self._history_cache:
            return list(self._history_cache[key])
        try:
            rows = self._parse_block(self._request_root(root, start_s, end_s, latest))
        except Exception:
            rows = []
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
        return {"oi_regime": cls.REGIMES[regime], "oi_regime_code": regime, "oi_strength": strength, "oi_zscore": None if oi_zscore is None else round(float(oi_zscore), 3), "volume_confirmation": None if volume_percent is None else cls._number(volume_percent) > 0}

    def _marketdata_analysis(self, contract_ticker, root, price_change_percent, volume_percent):
        row = self._request_marketdata(contract_ticker) if contract_ticker else self._request_marketdata_family(root)
        if not row:
            return None
        oi = self._number(row.get("openposition"))
        oi_change_contracts = self._number(row.get("oichange"))
        if oi <= 0:
            return None
        previous_oi = oi - oi_change_contracts
        oi_change_percent = (oi_change_contracts / previous_oi) * 100.0 if previous_oi > 0 else None
        ticker = str(row.get("secid") or row.get("ticker") or contract_ticker or "").upper()
        return {
            "oi_status": "AVAILABLE" if oi_change_percent is not None else "CURRENT_ONLY",
            "oi_source": "MOEX_FUTURES_MARKETDATA",
            "oi_root": root,
            "oi_contract_ticker": ticker,
            "oi": round(oi, 3),
            "oi_change_contracts": int(oi_change_contracts),
            "oi_change_percent": None if oi_change_percent is None else round(oi_change_percent, 3),
            "oi_data_date": row.get("tradedate") or row.get("systime") or None,
            "oi_service_version": self.VERSION,
            **self.classify(price_change_percent, oi_change_percent or 0.0, volume_percent, None),
        }

    def analyze(self, root, price_change_percent, volume_percent=None, as_of=None, contract_ticker=None):
        as_of = as_of or date.today()
        if isinstance(as_of, datetime):
            as_of = as_of.date()
        root = str(root).upper()
        current = self.load_all(as_of).get(root)
        if current:
            history = self.load_history(root, as_of - timedelta(days=self.HISTORY_DAYS), as_of)
            previous_oi = next((x["oi"] for x in reversed(history) if x.get("date") < as_of.isoformat()), None)
            oi_change = ((current["oi"] / previous_oi) - 1.0) * 100.0 if previous_oi and previous_oi > 0 else None
            changes = self._pct_changes([x["oi"] for x in history])
            z = self.zscore(oi_change, changes[-self.ZSCORE_WINDOW:]) if oi_change is not None else None
            return {"oi_status": "AVAILABLE" if oi_change is not None else "CURRENT_ONLY", "oi_source": "MOEX_ISS_FUTOI", "oi_root": root, "oi": current["oi"], "oi_long": current.get("oi_long"), "oi_short": current.get("oi_short"), "oi_change_percent": None if oi_change is None else round(oi_change, 3), "oi_history_days": len(history), "oi_service_version": self.VERSION, **self.classify(price_change_percent, oi_change or 0.0, volume_percent, z)}
        fallback = self._marketdata_analysis(contract_ticker, root, price_change_percent, volume_percent)
        if fallback:
            return fallback
        return {"oi_status": "UNAVAILABLE", "oi_source": "NONE", "oi_root": root, "oi_contract_ticker": str(contract_ticker or "").upper() or None, "oi_service_version": self.VERSION}
