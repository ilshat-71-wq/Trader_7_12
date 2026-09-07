from datetime import date
from services.open_interest_service import OpenInterestService


class FuturesOIScannerService:
    VERSION = "1.0.0"

    def __init__(self, api=None, oi_service=None):
        from api.bcs_api import BCSAPI
        self.api = api or BCSAPI()
        self.oi = oi_service or OpenInterestService()

    @staticmethod
    def _text(row, *keys):
        for key in keys:
            value = row.get(key) if isinstance(row, dict) else None
            if value not in (None, ""):
                return str(value).strip()
        return ""

    @staticmethod
    def _float(row, *keys):
        for key in keys:
            try:
                return float(row.get(key))
            except (TypeError, ValueError):
                pass
        return None

    @classmethod
    def _root(cls, ticker):
        ticker = str(ticker).upper().strip()
        return ticker.split("-", 1)[0]

    def _active_contracts(self):
        rows = self.api.get_instruments("FUTURES")
        today = date.today().isoformat()
        grouped = {}
        for row in rows if isinstance(rows, list) else []:
            ticker = self._text(row, "ticker", "secCode", "securityCode").upper()
            if not ticker:
                continue
            kind = self._text(row, "type", "instrumentType", "securityType").upper()
            if "OPTION" in kind or "OPT" in kind:
                continue
            expiry = self._text(row, "expirationDate", "expiration_date", "lastTradingDate", "expiryDate", "expiration") or "9999-99-99"
            if expiry < today:
                continue
            root = self._text(row, "underlyingAsset", "underlying", "assetCode", "baseAsset") or self._root(ticker)
            item = dict(row)
            item.update({"oi_root": root.upper(), "futures_ticker": ticker, "futures_class_code": self._text(row, "classCode", "class_code"), "_expiry": expiry})
            grouped.setdefault(root.upper(), []).append(item)
        return [sorted(items, key=lambda x: x["_expiry"])[0] for items in grouped.values()]

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}
        contracts = self._active_contracts()
        instruments = [{"ticker": x["futures_ticker"], "classCode": x["futures_class_code"]} for x in contracts if x.get("futures_class_code")]
        quotes = self.api.get_quotes_batch(instruments) if instruments else []
        quote_map = {self._text(q, "ticker", "secCode", "securityCode").upper(): q for q in quotes if isinstance(q, dict)}
        results, skipped = [], 0
        for contract in contracts:
            quote = quote_map.get(contract["futures_ticker"], {})
            last = self._float(quote, "lastPrice", "last", "price", "currentPrice", "close")
            opening = self._float(quote, "openPrice", "open", "dayOpen", "openingPrice")
            if last is None or opening is None or opening <= 0:
                skipped += 1
                continue
            change = (last / opening - 1.0) * 100.0
            volume = self._float(quote, "volume", "volumeContracts", "totalVolume", "volume24h")
            oi = self.oi.analyze(contract["oi_root"], change, None, as_of=as_of)
            row = dict(contract)
            row.update({"price": last, "change_percent": round(change, 4), "volume": volume, "oi_analysis": oi, "data_status": "AVAILABLE" if oi.get("oi_status") != "UNAVAILABLE" else "OI_UNAVAILABLE"})
            results.append(row)
        results.sort(key=lambda x: abs(float(x.get("oi_analysis", {}).get("oi_change_percent") or 0.0)), reverse=True)
        return results, {"status": "OK", "version": self.VERSION, "contracts": len(contracts), "analyzed": len(results), "skipped": skipped, "oi_source": "MOEX_ISS_FUTOI", "selection_policy": "NEAREST_NONEXPIRED_CONTRACT_PER_FUTURES_ROOT"}
