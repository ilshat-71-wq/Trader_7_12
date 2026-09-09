from datetime import date
from math import log1p

from services.futures_oi_scanner_service import FuturesOIScannerService


class FuturesOIMarketDataScannerService(FuturesOIScannerService):
    """MOEX RFUD futures OI scanner with current-session liquidity TOP."""

    VERSION = "2.7.3"
    LIQUIDITY_TOP_LIMIT = 20
    LIQUIDITY_PROBE_ROOTS = ("BR", "SI", "USDRUBF", "RI", "MX", "MM", "GD", "GL", "NG", "CL", "EU", "CR", "CNY")
    ECONOMIC_EXPOSURE_GROUPS = {
        "USD_RUB": {"SI", "USDRUBF"},
        "EUR_RUB": {"EU"},
        "CNY_RUB": {"CR", "CNY"},
        "GOLD": {"GD", "GL"},
        "MOEX_INDEX": {"MX", "MM"},
    }

    @classmethod
    def _economic_exposure_group(cls, family):
        family = str(family or "").upper()
        for group, roots in cls.ECONOMIC_EXPOSURE_GROUPS.items():
            if family in roots:
                return group
        return family

    @staticmethod
    def _family_to_underlying(family):
        family = str(family or "").upper()
        explicit = {
            "SBRF": "SBER",
            "SR": "SBER",
        }
        if family in explicit:
            return explicit[family]
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
            "SI": "USDRUB",
            "EU": "EURRUB",
            "CR": "CNYRUB",
            "NA": "QQQ",
            "SF": "SPYF",
            "MX": "MIX",
            "MM": "MXI",
            "RI": "RTS",
            "RM": "RTSM",
            "VI": "RVI",
        }
        return aliases.get(mapped, mapped)

    @staticmethod
    def _session_turnover(marketdata):
        """Read MOEX's exchange-supplied current-session monetary turnover.

        VALTODAY is the authoritative RFUD monetary turnover field. We do not
        silently substitute price*volume or another ambiguous value field.
        """
        for key in ("valtoday", "valtodayrub", "valtodayrur"):
            try:
                value = float(marketdata.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value, key.upper()
        return 0.0, "UNAVAILABLE"

    @staticmethod
    def _underlying_change_percent(quote):
        """Resolve base change from BCS quote fields without requiring OPEN."""
        if not isinstance(quote, dict):
            return None, "UNAVAILABLE"

        direct_keys = (
            "changePercent", "change_percent", "lastChangePercent",
            "lastchangeprcnt", "changePrcnt", "changePct", "pctChange",
        )
        for key in direct_keys:
            try:
                value = float(quote.get(key))
            except (TypeError, ValueError):
                continue
            return value, key

        last = FuturesOIMarketDataScannerService._float(quote, "lastPrice", "last", "price", "currentPrice", "close")
        opening = FuturesOIMarketDataScannerService._float(quote, "openPrice", "open", "dayOpen", "openingPrice")
        if last is not None and opening is not None and opening > 0:
            return (last / opening - 1.0) * 100.0, "LAST_VS_OPEN"

        previous = FuturesOIMarketDataScannerService._float(
            quote, "prevPrice", "previousPrice", "prevClose", "previousClose", "lastToPrevPrice", "lasttoprevprice"
        )
        if last is not None and previous is not None and previous > 0:
            return (last / previous - 1.0) * 100.0, "LAST_VS_PREVIOUS"
        return None, "UNAVAILABLE"

    @staticmethod
    def _liquidity_score(turnover_rub, oi, volume):
        return round(log1p(max(0.0, float(turnover_rub or 0.0))) * 100.0 + log1p(max(0.0, float(oi or 0.0))) * 3.0 + log1p(max(0.0, float(volume or 0.0))), 3)

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}

        bcs_contracts = self._active_contracts()
        underlying_quotes = self._underlying_quotes(bcs_contracts)
        if hasattr(self.oi, "marketdata_front_contracts"):
            front_contracts = self.oi.marketdata_front_contracts(as_of=as_of)
        else:
            front_contracts = {}
            for contract in bcs_contracts:
                family = str(contract.get("oi_root") or "").upper()
                if not family:
                    continue
                request_roots = [family]
                raw_root = self._root(contract.get("futures_ticker") or contract.get("ticker"))
                if raw_root and raw_root not in request_roots:
                    request_roots.append(raw_root)
                row = None
                for request_root in request_roots:
                    row = self.oi._request_marketdata_family(request_root)
                    if row:
                        break
                if row and self._float(row, "openposition", "oi", "openInterest") not in (None, 0) and self._float(row, "openposition", "oi", "openInterest") > 0:
                    front_contracts.setdefault(family, dict(row))
                    front_contracts[family]["_moex_family"] = family

        candidates = []
        skipped = 0
        oi_available = 0
        liquidity_available = 0
        base_change_available = 0
        turnover_source_counts = {}

        for family, marketdata in sorted(front_contracts.items()):
            secid = self._text(marketdata, "secid", "ticker", "securityCode").upper()
            if not secid:
                skipped += 1
                continue
            last = self._float(marketdata, "last", "lastPrice", "price", "currentPrice")
            change = self._float(marketdata, "lastchangeprcnt", "lastChangePrcnt", "lastChangePercent", "lasttoprevprice", "lastToPrevPrice")
            if change is None:
                previous = self._float(marketdata, "prevsettleprice", "prevSettlePrice", "prevprice", "lastSettlPrice")
                if last is not None and previous and previous > 0:
                    change = (last / previous - 1.0) * 100.0
            if last is None or change is None:
                skipped += 1
                continue

            volume = self._float(marketdata, "voltoday", "volume", "volumeContracts", "totalVolume")
            turnover_rub, turnover_source = self._session_turnover(marketdata)
            turnover_source_counts[turnover_source] = turnover_source_counts.get(turnover_source, 0) + 1

            oi = self.oi._marketdata_analysis(secid, family, change, None)
            if not oi or oi.get("oi_status") not in {"AVAILABLE", "CURRENT_ONLY"}:
                skipped += 1
                continue
            oi_available += 1
            if turnover_rub > 0:
                liquidity_available += 1

            underlying_ticker = self._known_underlying_ticker(family, bcs_contracts)
            underlying_quote = underlying_quotes.get(underlying_ticker, {})
            underlying_price = self._float(underlying_quote, "lastPrice", "last", "price", "currentPrice", "close")
            underlying_change, underlying_change_source = self._underlying_change_percent(underlying_quote)
            if underlying_change is not None:
                base_change_available += 1

            candidates.append({
                "futures_root": family, "oi_root": family, "futures_ticker": secid,
                "futures_ticker_normalized": secid, "futures_class_code": "RFUD",
                "curve_rank": 1, "curve_role": "FRONT",
                "_expiry": marketdata.get("_moex_expiry") or "9999-99-99",
                "underlying_ticker": underlying_ticker, "underlying_asset": underlying_ticker,
                "economic_exposure_group": self._economic_exposure_group(family),
                "price": last, "change_percent": round(change, 4), "volume": volume,
                "session_turnover_rub": round(turnover_rub, 2) if turnover_rub else 0.0,
                "turnover_source": turnover_source,
                "liquidity_available": bool(turnover_rub > 0),
                "liquidity_score": self._liquidity_score(turnover_rub, oi.get("oi"), volume),
                "oi_analysis": oi, "underlying_price": underlying_price,
                "underlying_change_percent": None if underlying_change is None else round(underlying_change, 4),
                "underlying_change_source": underlying_change_source,
                "underlying_data_status": "AVAILABLE" if underlying_price is not None else "UNAVAILABLE",
                "direction_alignment": (
                    "ALIGNED_UP" if underlying_change is not None and change > 0 and underlying_change > 0
                    else "ALIGNED_DOWN" if underlying_change is not None and change < 0 and underlying_change < 0
                    else "DIVERGENCE" if underlying_change is not None and change * underlying_change < 0
                    else "NEUTRAL"
                ),
                "data_status": "AVAILABLE",
            })

        candidates.sort(key=lambda x: (float(x.get("session_turnover_rub") or 0.0), float(x.get("liquidity_score") or 0.0), float((x.get("oi_analysis") or {}).get("oi") or 0.0)), reverse=True)
        liquidity_rows = [x for x in candidates if x.get("liquidity_available")]

        liquidity_probe = {}
        for rank, item in enumerate(liquidity_rows, 1):
            root = str(item.get("futures_root") or "").upper()
            if root in self.LIQUIDITY_PROBE_ROOTS:
                liquidity_probe[root] = {
                    "rank": rank,
                    "contract": item.get("futures_ticker"),
                    "turnover_rub": item.get("session_turnover_rub"),
                    "oi": (item.get("oi_analysis") or {}).get("oi"),
                }

        selected = liquidity_rows[: self.LIQUIDITY_TOP_LIMIT]
        if len(selected) < self.LIQUIDITY_TOP_LIMIT:
            selected_ids = {id(x) for x in selected}
            selected.extend(x for x in candidates if id(x) not in selected_ids)
            selected = selected[: self.LIQUIDITY_TOP_LIMIT]
        for rank, item in enumerate(selected, 1):
            item["liquidity_rank"] = rank
            item["liquidity_tier"] = "LIQUIDITY_TOP"

        economic_overlap = {}
        for item in candidates:
            group = str(item.get("economic_exposure_group") or "")
            if group:
                economic_overlap.setdefault(group, []).append(item.get("futures_root"))
        economic_overlap = {key: sorted(set(values)) for key, values in economic_overlap.items() if len(set(values)) > 1}

        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics.update({
            "status": "OK", "version": self.VERSION, "contracts": len(front_contracts),
            "analyzed": len(candidates), "returned": len(selected), "oi_available": oi_available,
            "skipped": skipped, "quote_instruments": len(underlying_quotes), "quote_records": len(underlying_quotes),
            "marketdata_oi_records": oi_available, "liquidity_available": liquidity_available,
            "liquidity_top_limit": self.LIQUIDITY_TOP_LIMIT, "liquidity_top_returned": len(selected),
            "liquidity_metric": "MOEX_RFUD_CURRENT_SESSION_MONETARY_TURNOVER",
            "turnover_source": "VALTODAY_ONLY",
            "turnover_source_counts": turnover_source_counts,
            "liquidity_probe_roots": liquidity_probe,
            "economic_overlap_groups": economic_overlap,
            "base_change_available": base_change_available,
            "base_change_missing": max(0, len(candidates) - base_change_available),
            "oi_source": "MOEX_FUTURES_MARKETDATA_PRIMARY",
            "mapping": "MOEX_RFUD_SECID_TO_FAMILY + BCS_UNDERLYING_CONTEXT",
            "selection_policy": "MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY",
            "liquidity_policy": "CURRENT_SESSION_TURNOVER_DESC_TOP_20; NO_SYNTHETIC_PRICE_X_VOLUME",
            "marketdata_source": "MOEX_ISS_FUTURES_FORTS_RFUD",
        })
        print("Futures OI diagnostics:", diagnostics)
        return selected, diagnostics
