from datetime import date

from services.futures_oi_scanner_service import FuturesOIScannerService


class FuturesOIMarketDataScannerService(FuturesOIScannerService):
    """Futures scanner using MOEX FORTS market data as the primary OI source.

    BCS remains the source of the broker instrument universe and underlying
    quotes. MOEX ISS FORTS market data supplies the actual front contract,
    price change, open interest and OI change. FUTOI remains available inside
    OpenInterestService as an optional participant-structure layer.
    """

    VERSION = "2.5.0"

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}

        contracts = self._active_contracts()
        underlying_quotes = self._underlying_quotes(contracts)
        results = []
        skipped = 0
        oi_available = 0
        marketdata_rows = 0

        for contract in contracts:
            root = str(contract.get("oi_root") or "").upper()
            if not root:
                skipped += 1
                continue

            marketdata = self.oi._request_marketdata_family(root)
            if not marketdata:
                skipped += 1
                continue
            marketdata_rows += 1

            last = self._float(marketdata, "last", "lastPrice", "price", "currentPrice")
            change = self._float(
                marketdata,
                "lasttoprevprice",
                "lastChangePrcnt",
                "lastChangePercent",
            )
            if change is None:
                previous = self._float(
                    marketdata,
                    "prevprice",
                    "prevSettlePrice",
                    "prevsettleprice",
                    "lastSettlPrice",
                )
                if last is not None and previous and previous > 0:
                    change = (last / previous - 1.0) * 100.0
            if last is None or change is None:
                skipped += 1
                continue

            volume = self._float(
                marketdata,
                "voltoday",
                "volume",
                "volumeContracts",
                "totalVolume",
            )
            oi = self.oi._marketdata_analysis(None, root, change, None)
            if oi and oi.get("oi_status") in {"AVAILABLE", "CURRENT_ONLY"}:
                oi_available += 1
            if not oi:
                oi = {
                    "oi_status": "UNAVAILABLE",
                    "oi_source": "NONE",
                    "oi_root": root,
                }

            moex_contract = self._text(
                marketdata,
                "secid",
                "ticker",
                "securityCode",
            ) or contract.get("futures_ticker")

            row = dict(contract)
            row.update({
                "futures_ticker": moex_contract,
                "futures_ticker_normalized": str(moex_contract or "").upper(),
                "futures_class_code": "RFUD",
                "curve_role": "FRONT",
                "price": last,
                "change_percent": round(change, 4),
                "volume": volume,
                "oi_analysis": oi,
            })

            underlying_ticker = str(row.get("underlying_ticker") or "").upper()
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

            row.update({
                "underlying_price": underlying_price,
                "underlying_change_percent": (
                    None if underlying_change is None else round(underlying_change, 4)
                ),
                "underlying_data_status": (
                    "AVAILABLE" if underlying_price is not None else "UNAVAILABLE"
                ),
                "direction_alignment": (
                    "ALIGNED_UP"
                    if underlying_change is not None and change > 0 and underlying_change > 0
                    else "ALIGNED_DOWN"
                    if underlying_change is not None and change < 0 and underlying_change < 0
                    else "DIVERGENCE"
                    if underlying_change is not None and change * underlying_change < 0
                    else "NEUTRAL"
                ),
                "data_status": (
                    "AVAILABLE" if oi.get("oi_status") != "UNAVAILABLE" else "OI_UNAVAILABLE"
                ),
            })
            results.append(row)

        results.sort(
            key=lambda x: abs(
                float((x.get("oi_analysis") or {}).get("oi_change_percent") or 0.0)
            ),
            reverse=True,
        )

        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics.update({
            "status": "OK",
            "version": self.VERSION,
            "contracts": len(contracts),
            "analyzed": len(results),
            "oi_available": oi_available,
            "skipped": skipped,
            "quote_instruments": 0,
            "quote_records": marketdata_rows,
            "marketdata_oi_records": oi_available,
            "oi_source": "MOEX_FUTURES_MARKETDATA_PRIMARY",
            "mapping": "BCS_UNDERLYING_TO_CANONICAL_MOEX_ROOT + MOEX_FORTS_MARKETDATA",
            "selection_policy": "MOEX_MARKETDATA_FRONT_NONZERO_OI_PER_ROOT",
            "marketdata_source": "MOEX_ISS_FUTURES_FORTS_RFUD",
        })
        print("Futures OI diagnostics:", diagnostics)
        return results, diagnostics
