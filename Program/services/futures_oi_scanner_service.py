from datetime import date

from services.open_interest_service import OpenInterestService


class FuturesOIScannerService:
    """Read-only futures OI scanner with generic futures -> underlying mapping."""

    VERSION = "2.0.0"

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
        ticker = str(ticker or "").upper().strip()
        return ticker.split("-", 1)[0]

    @classmethod
    def _underlying_code(cls, row):
        value = cls._text(
            row,
            "underlyingAsset",
            "underlying",
            "underlyingTicker",
            "underlyingSecCode",
            "assetCode",
            "baseAsset",
            "baseTicker",
        )
        return value.upper() if value else ""

    @staticmethod
    def _normalize_underlying_display(code):
        code = str(code or "").upper().strip()
        aliases = {
            "USDRUB_TOM": "USDRUB",
            "USDRUBTOM": "USDRUB",
            "USDRUBF": "USDRUB",
            "USD/RUB": "USDRUB",
        }
        return aliases.get(code, code)

    @classmethod
    def _contract_sort_key(cls, item):
        return item.get("_expiry", "9999-99-99")

    def _active_contracts(self):
        rows = self.api.get_instruments("FUTURES")
        today = date.today().isoformat()
        grouped = {}
        for raw in rows if isinstance(rows, list) else []:
            ticker = self._text(raw, "ticker", "secCode", "securityCode").upper()
            if not ticker:
                continue
            kind = self._text(raw, "type", "instrumentType", "securityType").upper()
            if "OPTION" in kind or "OPT" in kind:
                continue
            expiry = self._text(
                raw,
                "expirationDate",
                "expiration_date",
                "lastTradingDate",
                "expiryDate",
                "expiration",
            ) or "9999-99-99"
            if expiry < today:
                continue
            futures_root = self._root(ticker)
            underlying_source = self._underlying_code(raw)
            item = dict(raw)
            item.update(
                {
                    "futures_root": futures_root,
                    "oi_root": futures_root,
                    "futures_ticker": ticker,
                    "futures_class_code": self._text(raw, "classCode", "class_code"),
                    "underlying_asset_source": underlying_source,
                    "underlying_asset": self._normalize_underlying_display(underlying_source),
                    "underlying_ticker": self._text(raw, "underlyingTicker", "underlyingSecCode") or underlying_source,
                    "underlying_class_code": self._text(raw, "underlyingClassCode", "underlying_class_code", "underlyingClass"),
                    "_expiry": expiry,
                }
            )
            grouped.setdefault(futures_root, []).append(item)

        # Keep every active root, but mark the front and next contracts so
        # rollover is visible instead of silently replacing one maturity.
        result = []
        for root, items in grouped.items():
            ordered = sorted(items, key=self._contract_sort_key)
            for index, item in enumerate(ordered):
                item["curve_rank"] = index + 1
                item["curve_role"] = "FRONT" if index == 0 else "NEXT" if index == 1 else "DEFERRED"
            result.append(ordered[0])
        return result

    def _underlying_quotes(self, contracts):
        instruments = []
        for item in contracts:
            ticker = item.get("underlying_ticker")
            class_code = item.get("underlying_class_code")
            if ticker and class_code:
                instruments.append({"ticker": ticker, "classCode": class_code})
        if not instruments:
            return {}
        quotes = self.api.get_quotes_batch(instruments)
        return {
            self._text(q, "ticker", "secCode", "securityCode").upper(): q
            for q in quotes
            if isinstance(q, dict)
        }

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}

        contracts = self._active_contracts()
        instruments = [
            {"ticker": x["futures_ticker"], "classCode": x["futures_class_code"]}
            for x in contracts
            if x.get("futures_class_code")
        ]
        quotes = self.api.get_quotes_batch(instruments) if instruments else []
        quote_map = {
            self._text(q, "ticker", "secCode", "securityCode").upper(): q
            for q in quotes
            if isinstance(q, dict)
        }
        underlying_quotes = self._underlying_quotes(contracts)

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

            underlying_ticker = str(contract.get("underlying_ticker") or "").upper()
            underlying_quote = underlying_quotes.get(underlying_ticker, {})
            underlying_price = self._float(
                underlying_quote,
                "lastPrice",
                "last",
                "price",
                "currentPrice",
                "close",
            )
            underlying_open = self._float(
                underlying_quote,
                "openPrice",
                "open",
                "dayOpen",
                "openingPrice",
            )
            underlying_change = (
                (underlying_price / underlying_open - 1.0) * 100.0
                if underlying_price is not None and underlying_open and underlying_open > 0
                else None
            )

            row = dict(contract)
            row.update(
                {
                    "price": last,
                    "change_percent": round(change, 4),
                    "volume": volume,
                    "oi_analysis": oi,
                    "underlying_price": underlying_price,
                    "underlying_change_percent": None if underlying_change is None else round(underlying_change, 4),
                    "underlying_data_status": "AVAILABLE" if underlying_price is not None else "UNAVAILABLE",
                    "direction_alignment": (
                        "ALIGNED_UP"
                        if underlying_change is not None and change > 0 and underlying_change > 0
                        else "ALIGNED_DOWN"
                        if underlying_change is not None and change < 0 and underlying_change < 0
                        else "DIVERGENCE"
                        if underlying_change is not None and change * underlying_change < 0
                        else "NEUTRAL"
                    ),
                    "data_status": "AVAILABLE" if oi.get("oi_status") != "UNAVAILABLE" else "OI_UNAVAILABLE",
                }
            )
            results.append(row)

        results.sort(
            key=lambda x: abs(float(x.get("oi_analysis", {}).get("oi_change_percent") or 0.0)),
            reverse=True,
        )
        return results, {
            "status": "OK",
            "version": self.VERSION,
            "contracts": len(contracts),
            "analyzed": len(results),
            "skipped": skipped,
            "oi_source": "MOEX_ISS_FUTOI",
            "mapping": "BCS_FUTURES_METADATA_UNDERLYING",
            "selection_policy": "FRONT_NONEXPIRED_CONTRACT_PER_FUTURES_ROOT",
            "rollover_policy": "OI_IS_ROOT_LEVEL; FRONT_AND_NEXT_CONTRACTS_EXPOSED",
        }
