from datetime import date, datetime

from services.open_interest_service import OpenInterestService


class FuturesOIScannerService:
    """Read-only futures OI scanner with explicit MOEX root mapping."""

    VERSION = "2.3.1"
    ENRICH_BATCH_SIZE = 100
    DEFAULT_FUTURES_CLASS_CODE = "SPBFUT"

    MOEX_SHORT_CODE_BY_UNDERLYING = {
        "AFLT": "AF", "ALRS": "AL", "AFKS": "AK", "CHMF": "CH", "FEES": "FS",
        "GAZP": "GZ", "GMKN": "GK", "HYDR": "HY", "LKOH": "LK", "MGNT": "MN",
        "MOEX": "ME", "MTSI": "MT", "NLMK": "NM", "NOTK": "NK", "ROSN": "RN",
        "RTKM": "RT", "SBER": "SR", "SBERP": "SP", "SNGP": "SG", "SNGS": "SN",
        "TATN": "TT", "TATP": "TP", "TRNF": "TN", "VTBR": "VB", "MAGN": "MG",
        "PLZL": "PZ", "YDEX": "YD", "SMLT": "SS", "POSI": "PS", "SPBE": "SE",
        "RUAL": "RL", "PHOR": "PH", "PIKK": "PI", "POLY": "PO", "RSTI": "RE",
        "SIBN": "SO", "TCSI": "TI", "VKCO": "VK", "SPYF": "SF", "NASD": "NA",
        "QQQ": "NA", "WUSH": "WU", "MVID": "MV", "CBOM": "CM", "SGZH": "SZ",
        "FLOT": "FL", "BSPB": "BS", "BANE": "BN", "KMAZ": "KM", "ASTR": "AS",
        "SOFL": "S0", "SVCB": "SC", "RASP": "RA", "FESH": "FE", "RNFT": "RU",
        "LEAS": "LE", "BELUGA": "NB", "X5": "X5", "OZON": "ON", "DOMRF": "DR",
        "IVAT": "IV", "ENPG": "EA", "T": "TB", "ALIBABA": "BB", "BAIDU": "BD",
        "PDD": "DD", "JDCOM": "JD", "TENCENT": "TC", "XIA": "XI", "SAP": "AP",
        "SONY": "SY", "NOVARTIS": "NO", "TOYOTA": "TO", "KOREA": "KR", "SAMSUNG": "SK",
        "HYNIX": "HX", "FIXR": "FI", "RAGR": "RZ", "SI": "SI", "EU": "EU",
        "CNY": "CR", "GL": "GL", "S2": "SL", "IMOEX": "IM", "MIX": "MX",
        "MXI": "MM", "MOEXCNY": "MY", "RTS": "RI", "RTSM": "RM", "RVI": "VI",
        "HOME": "HO", "OGI": "OG", "MMI": "MA", "FNI": "FN", "CNI": "CS",
        "RGBI": "RB", "IMOEXF": "IMOEXF", "IPO": "IP", "ETH": "EH", "BTC": "BT",
        "SOL": "S3", "XRP": "XR", "TRX": "TX", "BNB": "BC", "RUONIA": "RF",
        "APPF": "APPF", "AMDF": "AMDF", "TSLAF": "TSLAF", "SNDKF": "SNDKF",
        "COHRF": "COHRF", "NBISF": "NBISF", "HOODF": "HOODF", "LITEF": "LITEF",
        "SP500F": "SP500F", "QQQF": "QQQF", "GAZPF": "GAZPF", "SBERF": "SBERF",
    }

    UNDERLYING_ALIASES = {
        "USDRUB_TOM": "SI", "USDRUBTOM": "SI", "USDRUBF": "SI", "USDRUB": "SI",
        "EURRUB_TOM": "EU", "EURRUBTOM": "EU", "EURRUBF": "EU", "EURRUB": "EU",
        "CNYRUB_TOM": "CR", "CNYRUBTOM": "CR", "CNYRUBF": "CR", "CNYRUB": "CR",
    }

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
        return str(ticker or "").upper().strip().split("-", 1)[0]

    @classmethod
    def _underlying_code(cls, row):
        value = cls._text(row, "underlyingAsset", "underlying", "underlyingTicker", "underlyingSecCode", "assetCode", "baseAsset", "baseTicker")
        return value.upper() if value else ""

    @classmethod
    def _oi_root_from_metadata(cls, row):
        value = cls._text(row, "shortCode", "short_code", "futuresShortCode", "futures_short_code", "derivativesTicker", "derivatives_ticker", "shortTicker", "shortTickerCode", "underlyingFuturesCode", "underlying_futures_code")
        return value.upper() if value else ""

    @classmethod
    def _known_oi_roots(cls):
        return {str(value).upper() for value in cls.MOEX_SHORT_CODE_BY_UNDERLYING.values()}

    @classmethod
    def _oi_root(cls, row, ticker, underlying):
        """Return a canonical MOEX FUTOI root, never a full contract ticker.

        BCS metadata fields named shortCode/derivativesTicker are not trusted
        blindly: in live metadata they may contain a contract identifier such
        as AFLT-9.26 or another non-canonical value. For standard underlyings,
        the explicit BCS underlying-to-MOEX mapping is authoritative. A
        metadata value is accepted only when it is itself a known canonical
        FUTOI root (including perpetual roots).
        """
        underlying = str(underlying or "").upper().strip()
        underlying = cls.UNDERLYING_ALIASES.get(underlying, underlying)
        mapped = cls.MOEX_SHORT_CODE_BY_UNDERLYING.get(underlying)
        if mapped:
            return mapped.upper()

        metadata_root = cls._oi_root_from_metadata(row)
        known_roots = cls._known_oi_roots()
        if metadata_root and "-" not in metadata_root and metadata_root in known_roots:
            return metadata_root

        ticker_root = cls._root(ticker)
        return ticker_root

    @staticmethod
    def _normalize_underlying_display(code):
        code = str(code or "").upper().strip()
        aliases = {"USDRUB_TOM": "USDRUB", "USDRUBTOM": "USDRUB", "USDRUBF": "USDRUB", "USD/RUB": "USDRUB"}
        return aliases.get(code, code)

    @staticmethod
    def _normalize_expiry(value):
        if value in (None, ""):
            return "9999-99-99"
        if isinstance(value, datetime):
            return value.date().isoformat()
        if hasattr(value, "isoformat") and not isinstance(value, str):
            try:
                return value.isoformat()[:10]
            except (TypeError, ValueError):
                pass
        text = str(value).strip()
        if not text:
            return "9999-99-99"
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                return datetime.fromisoformat(candidate).date().isoformat()
            except (TypeError, ValueError):
                pass
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(text[:10], fmt).date().isoformat()
            except ValueError:
                pass
        return "9999-99-99"

    @classmethod
    def _contract_sort_key(cls, item):
        return item.get("_expiry", "9999-99-99")

    @staticmethod
    def _metadata_class_code(row):
        if not isinstance(row, dict):
            return ""
        for key in ("classCode", "class_code", "classcode"):
            value = str(row.get(key) or "").strip()
            if value:
                return value
        boards = row.get("boards")
        if isinstance(boards, dict):
            boards = [boards]
        if isinstance(boards, list):
            candidates = []
            for board in boards:
                if not isinstance(board, dict):
                    continue
                code = ""
                for key in ("classCode", "class_code", "classcode"):
                    value = str(board.get(key) or "").strip()
                    if value:
                        code = value
                        break
                if code:
                    exchange = str(board.get("exchange") or board.get("exchangeName") or "").strip().upper()
                    candidates.append((exchange == "MOEX", code))
            for is_moex, code in candidates:
                if is_moex:
                    return code
            if candidates:
                return candidates[0][1]
        return ""

    @staticmethod
    def _metadata_expiry(row):
        if not isinstance(row, dict):
            return ""
        return FuturesOIScannerService._text(row, "expirationDate", "expiration_date", "lastTradingDate", "expiryDate", "expiration", "expiry")

    def _enrich_contract_metadata(self, rows):
        source_rows = [dict(row) for row in rows if isinstance(row, dict)]
        tickers = [self._text(row, "ticker", "secCode", "securityCode") for row in source_rows]
        tickers = [ticker for ticker in tickers if ticker]
        enriched, lookup_ok, lookup_records = {}, 0, 0
        for start in range(0, len(tickers), self.ENRICH_BATCH_SIZE):
            batch = tickers[start:start + self.ENRICH_BATCH_SIZE]
            try:
                records = self.api.get_instruments_by_tickers(batch)
            except Exception as exc:
                print("⚠️ Futures metadata lookup failed:", type(exc).__name__)
                continue
            lookup_ok += 1
            lookup_records += len(records) if isinstance(records, list) else 0
            for record in records if isinstance(records, list) else []:
                ticker = self._text(record, "ticker", "secCode", "securityCode")
                if ticker:
                    enriched[ticker.upper()] = record

        result = []
        metadata_class_code_available = metadata_expiry_available = metadata_oi_root_available = 0
        for row in source_rows:
            ticker = self._text(row, "ticker", "secCode", "securityCode")
            meta = enriched.get(ticker.upper(), {})
            merged = dict(row)
            merged.update({k: v for k, v in meta.items() if v not in (None, "")})
            class_code = self._metadata_class_code(meta) or self._metadata_class_code(row)
            expiry = self._metadata_expiry(meta) or self._metadata_expiry(row)
            if class_code:
                merged["classCode"] = class_code
                metadata_class_code_available += 1
            if expiry:
                merged["expirationDate"] = expiry
                metadata_expiry_available += 1
            if self._oi_root_from_metadata(meta) or self._oi_root_from_metadata(row):
                metadata_oi_root_available += 1
            result.append(merged)
        return result, {
            "metadata_lookup_batches": (len(tickers) + self.ENRICH_BATCH_SIZE - 1) // self.ENRICH_BATCH_SIZE,
            "metadata_lookup_ok": lookup_ok,
            "metadata_lookup_records": lookup_records,
            "metadata_class_code_available": metadata_class_code_available,
            "metadata_expiry_available": metadata_expiry_available,
            "metadata_oi_root_available": metadata_oi_root_available,
        }

    def _active_contracts(self):
        rows = self.api.get_instruments("FUTURES")
        raw_count = len(rows) if isinstance(rows, list) else 0
        rows, metadata_diag = self._enrich_contract_metadata(rows)
        today = date.today().isoformat()
        grouped = {}
        diagnostics = {
            "raw_contracts": raw_count, "option_filtered": 0, "expired_filtered": 0,
            "active_contracts": 0, "active_roots": 0, "class_code_available": 0,
            "class_code_fallback": 0, "expiry_available": 0, "oi_root_mapping": 0,
            "oi_root_fallback": 0, **metadata_diag,
        }
        for raw in rows:
            source_ticker = self._text(raw, "ticker", "secCode", "securityCode")
            if not source_ticker:
                continue
            ticker = source_ticker.upper()
            kind = self._text(raw, "type", "instrumentType", "securityType").upper()
            if "OPTION" in kind or "OPT" in kind:
                diagnostics["option_filtered"] += 1
                continue
            expiry_raw = self._metadata_expiry(raw)
            expiry = self._normalize_expiry(expiry_raw)
            if expiry_raw:
                diagnostics["expiry_available"] += 1
            if expiry < today:
                diagnostics["expired_filtered"] += 1
                continue
            futures_root = self._root(ticker)
            underlying_source = self._underlying_code(raw)
            oi_root = self._oi_root(raw, ticker, underlying_source)
            if oi_root:
                diagnostics["oi_root_mapping"] += 1
            else:
                diagnostics["oi_root_fallback"] += 1
                oi_root = futures_root
            class_code = self._metadata_class_code(raw)
            if class_code:
                diagnostics["class_code_available"] += 1
            else:
                class_code = self.DEFAULT_FUTURES_CLASS_CODE
                diagnostics["class_code_fallback"] += 1
            item = dict(raw)
            item.update({
                "futures_root": futures_root, "oi_root": oi_root, "futures_ticker": source_ticker,
                "futures_ticker_normalized": ticker, "futures_class_code": class_code,
                "underlying_asset_source": underlying_source,
                "underlying_asset": self._normalize_underlying_display(underlying_source),
                "underlying_ticker": self._text(raw, "underlyingTicker", "underlyingSecCode") or underlying_source,
                "underlying_class_code": self._text(raw, "underlyingClassCode", "underlying_class_code", "underlyingClass"),
                "_expiry": expiry,
            })
            grouped.setdefault(oi_root, []).append(item)

        result = []
        for root, items in grouped.items():
            ordered = sorted(items, key=self._contract_sort_key)
            for index, item in enumerate(ordered):
                item["curve_rank"] = index + 1
                item["curve_role"] = "FRONT" if index == 0 else "NEXT" if index == 1 else "DEFERRED"
            result.append(ordered[0])
        diagnostics["active_contracts"] = len(result)
        diagnostics["active_roots"] = len(grouped)
        self._last_contract_diagnostics = diagnostics
        print("Futures OI metadata:", diagnostics)
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
        return {self._text(q, "ticker", "secCode", "securityCode").upper(): q for q in quotes if isinstance(q, dict)}

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}
        contracts = self._active_contracts()
        instruments = [{"ticker": x["futures_ticker"], "classCode": x["futures_class_code"]} for x in contracts if x.get("futures_class_code")]
        quotes = self.api.get_quotes_batch(instruments) if instruments else []
        quote_map = {self._text(q, "ticker", "secCode", "securityCode").upper(): q for q in quotes if isinstance(q, dict)}
        underlying_quotes = self._underlying_quotes(contracts)
        results, skipped, oi_available = [], 0, 0
        for contract in contracts:
            quote = quote_map.get(contract["futures_ticker"].upper(), {})
            last = self._float(quote, "lastPrice", "last", "price", "currentPrice", "close")
            opening = self._float(quote, "openPrice", "open", "dayOpen", "openingPrice")
            if last is None or opening is None or opening <= 0:
                skipped += 1
                continue
            change = (last / opening - 1.0) * 100.0
            volume = self._float(quote, "volume", "volumeContracts", "totalVolume", "volume24h")
            oi = self.oi.analyze(contract["oi_root"], change, None, as_of=as_of)
            if oi.get("oi_status") in {"AVAILABLE", "CURRENT_ONLY"}:
                oi_available += 1
            underlying_ticker = str(contract.get("underlying_ticker") or "").upper()
            underlying_quote = underlying_quotes.get(underlying_ticker, {})
            underlying_price = self._float(underlying_quote, "lastPrice", "last", "price", "currentPrice", "close")
            underlying_open = self._float(underlying_quote, "openPrice", "open", "dayOpen", "openingPrice")
            underlying_change = ((underlying_price / underlying_open - 1.0) * 100.0 if underlying_price is not None and underlying_open and underlying_open > 0 else None)
            row = dict(contract)
            row.update({
                "price": last, "change_percent": round(change, 4), "volume": volume, "oi_analysis": oi,
                "underlying_price": underlying_price,
                "underlying_change_percent": None if underlying_change is None else round(underlying_change, 4),
                "underlying_data_status": "AVAILABLE" if underlying_price is not None else "UNAVAILABLE",
                "direction_alignment": (
                    "ALIGNED_UP" if underlying_change is not None and change > 0 and underlying_change > 0
                    else "ALIGNED_DOWN" if underlying_change is not None and change < 0 and underlying_change < 0
                    else "DIVERGENCE" if underlying_change is not None and change * underlying_change < 0
                    else "NEUTRAL"
                ),
                "data_status": "AVAILABLE" if oi.get("oi_status") != "UNAVAILABLE" else "OI_UNAVAILABLE",
            })
            results.append(row)
        results.sort(key=lambda x: abs(float(x.get("oi_analysis", {}).get("oi_change_percent") or 0.0)), reverse=True)
        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics.update({
            "status": "OK", "version": self.VERSION, "contracts": len(contracts), "analyzed": len(results),
            "oi_available": oi_available, "skipped": skipped, "quote_instruments": len(instruments),
            "quote_records": len(quotes), "oi_source": "MOEX_ISS_FUTOI",
            "mapping": "BCS_UNDERLYING_TO_CANONICAL_MOEX_SHORT_CODE",
            "selection_policy": "FRONT_NONEXPIRED_CONTRACT_PER_MOEX_OI_ROOT",
            "rollover_policy": "OI_IS_ROOT_LEVEL; FRONT_AND_NEXT_CONTRACTS_EXPOSED",
        })
        return results, diagnostics
