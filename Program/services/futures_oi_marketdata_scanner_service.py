from datetime import date

from services.futures_oi_scanner_service import FuturesOIScannerService


class FuturesOIMarketDataScannerService(FuturesOIScannerService):
    """Futures scanner using MOEX RFUD market data as the primary OI source.

    MOEX RFUD is the authoritative source for the actual traded contract,
    front-contract selection, price change, open interest and OI change. BCS
    remains useful for broker context and underlying quotes, while FUTOI stays
    optional participant-structure context.
    """

    VERSION = "2.6.0"

    @staticmethod
    def _family_to_underlying(family):
        family = str(family or "").upper()
        reverse = {}
        for root, prefix in FuturesOIScannerService.__dict__.get("MOEX_SHORT_CODE_BY_UNDERLYING", {}).items():
            reverse.setdefault(str(prefix).upper(), str(root).upper())
        return reverse.get(family, family)

    @classmethod
    def _known_underlying_ticker(cls, family, contracts):
        family = str(family or "").upper()
        for contract in contracts:
            if str(contract.get("oi_root") or "").upper() == family:
                ticker = str(contract.get("underlying_ticker") or "").upper()
                if ticker:
                    return ticker
        mapped = cls._family_to_underlying(family)
        aliases = {
            "SI": "USDRUB", "EU": "EURRUB", "CR": "CNYRUB",
            "NA": "QQQ", "SF": "SPYF", "MX": "MIX", "MM": "MXI",
            "RI": "RTS", "RM": "RTSM", "VI": "RVI",
        }
        return aliases.get(mapped, mapped)

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}

        # BCS is used for broker universe/context. It is NOT used to decide
        # which RFUD contract is front: BCS metadata may omit expiry or expose
        # a contract identifier where an underlying code is expected.
        bcs_contracts = self._active_contracts()
        underlying_quotes = self._underlying_quotes(bcs_contracts)
        front_contracts = self.oi.marketdata_front_contracts(as_of=as_of)

        results = []
        skipped = 0
        oi_available = 0

        for family, marketdata in sorted(front_contracts.items()):
            secid = self._text(marketdata, "secid", "ticker", "securityCode").upper()
            if not secid:
                skipped += 1
                continue

            last = self._float(marketdata, "last", "lastPrice", "price", "currentPrice")
            change = self._float(
                marketdata,
                "lastchangeprcnt",
                "lastChangePrcnt",
                "lastChangePercent",
            )
            if change is None:
                previous = self._float(
                    marketdata,
                    "prevsettleprice",
                    "prevSettlePrice",
                    "prevprice",
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
            oi = self.oi._marketdata_analysis(secid, family, change, None)
            if not oi or oi.get("oi_status") not in {"AVAILABLE", "CURRENT_ONLY"}:
                skipped += 1
                continue
            oi_available += 1

            underlying_ticker = self._known_underlying_ticker(family, bcs_contracts)
            underlying_quote = underlying_quotes.get(underlying_ticker, {})
            underlying_price = self._float(
                underlying_quote,
                "lastPrice", "last", "price", "currentPrice", "close",
            )
            underlying_open = self._float(
                underlying_quote,
                "openPrice", "open", "dayOpen", "openingPrice",
            )
            underlying_change = (
                (underlying_price / underlying_open - 1.0) * 100.0
                if underlying_price is not None and underlying_open and underlying_open > 0
                else None
            )

            row = {
                "futures_root": family,
                "oi_root": family,
                "futures_ticker": secid,
                "futures_ticker_normalized": secid,
                "futures_class_code": "RFUD",
                "curve_rank": 1,
                "curve_role": "FRONT",
                "_expiry": marketdata.get("_moex_expiry") or "9999-99-99",
                "underlying_ticker": underlying_ticker,
                "underlying_asset": underlying_ticker,
                "price": last,
                "change_percent": round(change, 4),
                "volume": volume,
                "oi_analysis": oi,
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
                "data_status": "AVAILABLE",
            }
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
            "contracts": len(front_contracts),
            "analyzed": len(results),
            "oi_available": oi_available,
            "skipped": skipped,
            "quote_instruments": len(underlying_quotes),
            "quote_records": len(underlying_quotes),
            "marketdata_oi_records": oi_available,
            "oi_source": "MOEX_FUTURES_MARKETDATA_PRIMARY",
            "mapping": "MOEX_RFUD_SECID_TO_FAMILY + BCS_UNDERLYING_CONTEXT",
            "selection_policy": "MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY",
            "marketdata_source": "MOEX_ISS_FUTURES_FORTS_RFUD",
        })
        print("Futures OI diagnostics:", diagnostics)
        return results, diagnostics
