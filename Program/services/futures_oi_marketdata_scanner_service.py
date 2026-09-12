from datetime import date, datetime, time, timezone
from math import log1p
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from services.futures_oi_scanner_service import FuturesOIScannerService


class FuturesOIMarketDataScannerService(FuturesOIScannerService):
    """MOEX RFUD futures OI scanner with current-day liquidity TOP."""

    VERSION = "2.7.11"
    LIQUIDITY_TOP_LIMIT = 20
    LIQUIDITY_PROBE_ROOTS = ("BR", "SI", "USDRUBF", "RI", "MX", "MM", "GD", "GL", "NG", "CL", "EU", "CR", "CNY")
    ECONOMIC_EXPOSURE_GROUPS = {
        "USD_RUB": {"SI", "USDRUBF"}, "EUR_RUB": {"EU"}, "CNY_RUB": {"CR", "CNY"},
        "GOLD": {"GD", "GL"}, "MOEX_INDEX": {"MX", "MM"},
    }
    MARKETDATA_PAGE_SIZE = 100
    MARKETDATA_MAX_PAGES = 10
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    RADAR_START = time(7, 0)
    UNDERLYING_CANDLE_INTERVAL = "M5"

    def __init__(self, api=None, oi_service=None):
        super().__init__(api=api, oi_service=oi_service)
        oi_cls = type(self.oi)
        try:
            if getattr(oi_cls, "TIMEOUT", 0) < 15:
                setattr(oi_cls, "TIMEOUT", 15)
        except (TypeError, AttributeError):
            pass
        try:
            if getattr(oi_cls, "MARKETDATA_RETRIES", 0) < 3:
                setattr(oi_cls, "MARKETDATA_RETRIES", 3)
        except (TypeError, AttributeError):
            pass
        self._underlying_class_codes = {}
        self._underlying_family_tickers = {}
        self._underlying_bcs_tickers = {}
        self._underlying_mapping_source = {}
        self._underlying_day_change_cache = {}

    @classmethod
    def _economic_exposure_group(cls, family):
        family = str(family or "").upper()
        for group, roots in cls.ECONOMIC_EXPOSURE_GROUPS.items():
            if family in roots:
                return group
        return family

    @staticmethod
    def _normalize_mapping_text(value):
        return "".join(ch for ch in str(value or "").upper() if ch.isalnum())

    @classmethod
    def _semantic_aliases(cls, value):
        normalized = cls._normalize_mapping_text(value)
        if not normalized:
            return set()
        aliases = {normalized}
        if normalized == "GLDRUBTOM":
            aliases.add("GLDRUB")
        replacements = {
            "СБЕРБАНК": {"SBER", "SBERBANK", "SBRF"},
            "ЛУКОЙЛ": {"LKOH", "LUKOIL"},
            "ЗОЛОТОРАСЧЕТНЫЙ": {"GLDRUBTOM", "GLDRUB", "GOLD"},
            "ЗОЛОТО": {"GLDRUBTOM", "GLDRUB", "GOLD"},
            "USDРUB": {"USDRUB", "USDRUBTOM"},
            "USDRUB": {"USDRUBTOM"},
            "EURRUB": {"EURRUBTOM"},
            "CNYRUB": {"CNYRUBTOM"},
        }
        for key, values in replacements.items():
            if normalized == cls._normalize_mapping_text(key):
                aliases.update(cls._normalize_mapping_text(x) for x in values)
        return aliases

    @staticmethod
    def _family_to_underlying(family):
        family = str(family or "").upper()
        explicit = {
            "SBRF": "SBER", "SR": "SBER", "LK": "LKOH",
            "GD": "GLDRUB_TOM", "GL": "GLDRUB_TOM",
            "SI": "USDRUB", "USDRUBF": "USDRUB",
            "EU": "EURRUB", "CR": "CNYRUB",
            # MIX and MXI are different futures contracts with the same
            # economic base asset: the IMOEX index. IMOEXF is another
            # futures contract on that same index, not the base itself.
            "MX": "IMOEX", "MM": "IMOEX", "IMOEXF": "IMOEX",
            "RI": "RTS", "RM": "RTS", "VI": "RVI",
            "NA": "QQQ", "SF": "SPY", "SP500F": "SP500",
            "BR": "BR", "CL": "CL", "NG": "NG",
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
        mapped = cls._family_to_underlying(family)
        aliases = {
            "SI": "USDRUB", "EU": "EURRUB", "CR": "CNYRUB",
            "NA": "QQQ", "SF": "SPY", "SP500F": "SP500",
            "MX": "IMOEX", "MM": "IMOEX", "RI": "RTS", "RM": "RTS",
            "VI": "RVI", "IMOEXF": "IMOEX",
        }
        canonical = aliases.get(mapped, mapped)
        normalized_canonical = cls._normalize_mapping_text(canonical)
        canonical_aliases = {
            "USDRUB": "USDRUB", "USDRUBTOM": "USDRUB",
            "EURRUB": "EURRUB", "EURRUBTOM": "EURRUB",
            "CNYRUB": "CNYRUB", "CNYRUBTOM": "CNYRUB",
            "GLDRUB": "GLDRUB_TOM", "GLDRUBTOM": "GLDRUB_TOM",
        }
        canonical = canonical_aliases.get(normalized_canonical, canonical)
        for contract in contracts:
            if str(contract.get("oi_root") or "").upper() == family:
                ticker = str(contract.get("underlying_ticker") or "").upper()
                if ticker and ticker != family and ticker not in {"СБЕРБАНК", "ЛУКОЙЛ", "ЗОЛОТО РАСЧЕТНЫЙ", "НЕФТЬ BRENT", "ПРИРОДНЫЙ ГАЗ", "ИНДЕКС МОСБИРЖИ", "ИНДЕКС IMOEX МИНИ"}:
                    return ticker
        return canonical

    @staticmethod
    def _select_underlying_class_code(record):
        if not isinstance(record, dict):
            return ""
        direct = str(record.get("classCode") or record.get("class_code") or record.get("classcode") or "").strip()
        if direct:
            return direct
        boards = record.get("boards")
        if isinstance(boards, dict):
            boards = [boards]
        candidates = []
        for board in boards or []:
            if not isinstance(board, dict):
                continue
            code = str(board.get("classCode") or board.get("class_code") or board.get("classcode") or "").strip()
            if not code:
                continue
            exchange = str(board.get("exchange") or board.get("exchangeName") or "").strip().upper()
            priority = 0 if exchange == "MOEX" else 1 if exchange == "SPB" else 2
            candidates.append((priority, code))
        return min(candidates)[1] if candidates else ""

    @staticmethod
    def _is_real_underlying_record(record):
        """Allow only real spot/base instrument types for underlying analysis."""
        if not isinstance(record, dict):
            return False
        instrument_type = str(record.get("instrumentType") or record.get("instrument_type") or record.get("type") or "").strip().upper()
        if instrument_type in {"FUTURES", "OPTIONS"}:
            return False
        allowed_types = {"CURRENCY", "STOCK", "FOREIGN_STOCK", "ETF", "GOODS", "INDICES"}
        return not instrument_type or instrument_type in allowed_types

    def _underlying_quotes(self, contracts):
        requested = {}
        family_tickers = {}
        raw_semantics = {}
        for item in contracts:
            family = self._text(item, "oi_root", "futures_root").upper()
            if not family:
                continue
            mapped = self._family_to_underlying(family)
            raw = self._text(item, "underlying_ticker", "underlyingTicker", "underlyingSecCode").upper()
            ticker = mapped
            if raw and raw not in {family, "СБЕРБАНК", "ЛУКОЙЛ", "ЗОЛОТО РАСЧЕТНЫЙ", "НЕФТЬ BRENT", "ПРИРОДНЫЙ ГАЗ", "ИНДЕКС МОСБИРЖИ", "ИНДЕКС IMOEX МИНИ"}:
                ticker = raw
            canonical = ticker.upper()
            normalized_ticker = self._normalize_mapping_text(canonical)
            ticker_aliases = {"USDRUB": "USDRUB", "USDRUBTOM": "USDRUB", "EURRUB": "EURRUB", "EURRUBTOM": "EURRUB", "CNYRUB": "CNYRUB", "CNYRUBTOM": "CNYRUB", "GLDRUB": "GLDRUB_TOM", "GLDRUBTOM": "GLDRUB_TOM"}
            canonical = ticker_aliases.get(normalized_ticker, canonical)
            family_tickers[family] = canonical
            raw_semantics[family] = raw
            item_class = self._text(item, "underlying_class_code", "underlyingClassCode", "underlying_class_code")
            entry = requested.setdefault(canonical, {"ticker": canonical, "classCode": "", "families": set()})
            entry["families"].add(family)
            if item_class and not entry["classCode"]:
                entry["classCode"] = item_class

        unresolved = [key for key, item in requested.items() if not item.get("classCode")]
        lookup_batches = 0
        lookup_records = 0
        semantic_matches = 0
        for start in range(0, len(unresolved), self.ENRICH_BATCH_SIZE):
            batch = unresolved[start:start + self.ENRICH_BATCH_SIZE]
            lookup_batches += 1
            try:
                records = self.api.get_instruments_by_tickers(batch)
            except Exception as exc:
                print("⚠️ Underlying metadata lookup failed:", type(exc).__name__)
                continue
            if not isinstance(records, list):
                continue
            lookup_records += len(records)
            for record in records:
                if not self._is_real_underlying_record(record):
                    continue
                actual_ticker = self._text(record, "_underlying_bcs_ticker", "ticker", "secCode", "securityCode").upper()
                class_code = self._text(record, "_underlying_bcs_class_code", "classCode", "class_code", "classcode") or self._select_underlying_class_code(record)
                if not actual_ticker or not class_code:
                    continue
                record_values = []
                for key in ("ticker", "secCode", "securityCode", "baseAssetTicker", "base_asset_ticker", "underlyingAsset", "underlying_asset", "underlying", "underlyingTicker", "underlying_ticker", "underlyingSecCode", "underlying_sec_code", "assetCode", "asset_code", "baseAsset", "base_asset", "baseTicker", "base_ticker", "shortCode", "short_code", "shortName", "name", "fullName"):
                    value = record.get(key)
                    if value:
                        record_values.append(value)
                record_aliases = set()
                for value in record_values:
                    record_aliases.update(self._semantic_aliases(value))
                for economic_ticker, entry in requested.items():
                    wanted = set(self._semantic_aliases(economic_ticker))
                    for family in entry["families"]:
                        wanted.update(self._semantic_aliases(family))
                        wanted.update(self._semantic_aliases(raw_semantics.get(family)))
                    if not wanted.intersection(record_aliases):
                        continue
                    entry["classCode"] = class_code
                    entry["bcsTicker"] = actual_ticker
                    entry["mappingSource"] = "BCS_SEMANTIC_METADATA"
                    semantic_matches += 1

        self._underlying_class_codes = {key: value["classCode"] for key, value in requested.items() if value.get("classCode")}
        self._underlying_bcs_tickers = {key: value["bcsTicker"] for key, value in requested.items() if value.get("bcsTicker")}
        self._underlying_mapping_source = {key: value["mappingSource"] for key, value in requested.items() if value.get("mappingSource")}
        self._underlying_family_tickers = family_tickers
        self._underlying_metadata_diagnostics = {"underlying_requested": len(requested), "underlying_class_codes": len(self._underlying_class_codes), "underlying_class_code_missing": max(0, len(requested) - len(self._underlying_class_codes)), "underlying_metadata_lookup_batches": lookup_batches, "underlying_metadata_lookup_records": lookup_records, "underlying_semantic_matches": semantic_matches}
        instruments = []
        for economic_ticker, item in requested.items():
            class_code = item.get("classCode")
            bcs_ticker = item.get("bcsTicker") or economic_ticker
            if class_code and bcs_ticker:
                instruments.append({"ticker": bcs_ticker, "classCode": class_code})
        if not instruments:
            return {}
        try:
            quotes = self.api.get_quotes_batch(instruments)
        except Exception as exc:
            print("⚠️ Underlying quotes lookup failed:", type(exc).__name__)
            return {}
        return {self._text(q, "ticker", "secCode", "securityCode").upper(): q for q in quotes if isinstance(q, dict)}

    @staticmethod
    def _session_turnover(marketdata):
        for key in ("valtoday", "valtodayrub", "valtodayrur"):
            try:
                value = float(marketdata.get(key))
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return 0.0

    @staticmethod
    def _session_turnover_source(marketdata):
        for key in ("valtoday", "valtodayrub", "valtodayrur"):
            try:
                if float(marketdata.get(key)) > 0:
                    return key.upper()
            except (TypeError, ValueError):
                continue
        return "UNAVAILABLE"

    @staticmethod
    def _underlying_change_percent(quote):
        if not isinstance(quote, dict):
            return None, "UNAVAILABLE"
        direct_keys = ("changePercent", "change_percent", "lastChangePercent", "lastchangeprcnt", "changePrcnt", "changePct", "pctChange")
        for key in direct_keys:
            try:
                value = float(quote.get(key))
            except (TypeError, ValueError):
                continue
            return round(value, 6), key
        last = FuturesOIMarketDataScannerService._float(quote, "lastPrice", "last", "price", "currentPrice", "close")
        opening = FuturesOIMarketDataScannerService._float(quote, "openPrice", "open", "dayOpen", "openingPrice")
        if last is not None and opening is not None and opening > 0:
            return round((last / opening - 1.0) * 100.0, 6), "LAST_VS_OPEN"
        previous_close = FuturesOIMarketDataScannerService._float(quote, "prevClose", "previousClose", "previous_close", "prev_close")
        if last is not None and previous_close is not None and previous_close > 0:
            return round((last / previous_close - 1.0) * 100.0, 6), "LAST_VS_PREVIOUS"
        return None, "UNAVAILABLE"

    @staticmethod
    def _candle_value(row, *keys):
        if not isinstance(row, dict):
            return None
        for key in keys:
            value = row.get(key)
            try:
                if value is not None:
                    return float(value)
            except (TypeError, ValueError):
                continue
        return None

    @classmethod
    def _candle_datetime(cls, row):
        value = row.get("dateTime") if isinstance(row, dict) else None
        if value is None and isinstance(row, dict):
            value = row.get("datetime") or row.get("date") or row.get("time") or row.get("timestamp")
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value / 1000.0 if value > 10_000_000_000 else value, tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                return None
        if not value:
            return None
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=cls.MOSCOW_TZ)
        return parsed.astimezone(cls.MOSCOW_TZ)

    def _underlying_day_change(self, ticker):
        ticker = str(ticker or "").upper()
        if ticker in self._underlying_day_change_cache:
            return self._underlying_day_change_cache[ticker]
        economic_ticker = ticker
        bcs_ticker = self._underlying_bcs_tickers.get(economic_ticker, economic_ticker)
        class_code = self._underlying_class_codes.get(economic_ticker)
        if not class_code:
            result = (None, "NO_CLASS_CODE")
            self._underlying_day_change_cache[ticker] = result
            return result
        now = datetime.now(self.MOSCOW_TZ)
        start = datetime.combine(now.date(), self.RADAR_START, tzinfo=self.MOSCOW_TZ)
        if now < start:
            result = (None, "BEFORE_07:00")
            self._underlying_day_change_cache[ticker] = result
            return result
        try:
            bars = self.api.get_candles(bcs_ticker, class_code, interval=self.UNDERLYING_CANDLE_INTERVAL, start_time=start.astimezone(timezone.utc), end_time=now.astimezone(timezone.utc))
        except Exception as exc:
            result = (None, f"CANDLE_ERROR:{type(exc).__name__}")
            self._underlying_day_change_cache[ticker] = result
            return result
        rows = bars.get("candles", bars.get("bars", [])) if isinstance(bars, dict) else bars
        valid = []
        for row in rows if isinstance(rows, list) else []:
            dt = self._candle_datetime(row)
            opening = self._candle_value(row, "open", "openPrice")
            close = self._candle_value(row, "close", "closePrice")
            if dt is not None and start <= dt <= now and opening and opening > 0 and close is not None:
                valid.append((dt, opening, close))
        if not valid:
            result = (None, "NO_07:00_NOW_CANDLES")
        else:
            valid.sort(key=lambda item: item[0])
            result = (round((valid[-1][2] / valid[0][1] - 1.0) * 100.0, 6), "BCS_M5_07:00_NOW")
        self._underlying_day_change_cache[ticker] = result
        return result

    @staticmethod
    def _liquidity_score(turnover_rub, oi, volume):
        return round(log1p(max(0.0, float(turnover_rub or 0.0))) * 100.0 + log1p(max(0.0, float(oi or 0.0))) * 3.0 + log1p(max(0.0, float(volume or 0.0))), 3)

    def _load_marketdata_all_resilient(self):
        oi = self.oi
        cached = getattr(oi, "_marketdata_all_cache", None)
        if cached:
            return list(cached), None
        http_get = getattr(oi, "_http_get", None)
        base_url = getattr(oi, "FUTURES_MARKETDATA_URL", "https://iss.moex.com/iss/engines/futures/markets/forts/boards/RFUD/securities")
        parse_block = getattr(oi, "_parse_block", None)
        if not http_get or not parse_block:
            return [], "MOEX_MARKETDATA_CLIENT_UNAVAILABLE"
        rows, page_errors = [], []
        for page in range(self.MARKETDATA_MAX_PAGES):
            start = page * self.MARKETDATA_PAGE_SIZE
            params = {"iss.only": "marketdata", "start": start, "limit": self.MARKETDATA_PAGE_SIZE}
            url = f"{base_url}.json?{urlencode(params)}"
            try:
                payload = http_get(url, timeout=getattr(oi, "TIMEOUT", 15))
                page_rows = parse_block(payload, "marketdata")
            except Exception as exc:
                page_errors.append(f"page={page}: {type(exc).__name__}")
                break
            if not page_rows:
                break
            rows.extend(page_rows)
            if len(page_rows) < self.MARKETDATA_PAGE_SIZE:
                break
        deduped = {}
        for row in rows:
            if isinstance(row, dict):
                secid = str(row.get("secid") or row.get("ticker") or "").upper()
                if secid:
                    deduped[secid] = row
        result = list(deduped.values())
        if result:
            oi._marketdata_all_cache = list(result)
            return result, None
        return [], "; ".join(page_errors) if page_errors else "MOEX_MARKETDATA_EMPTY"

    def scan(self, as_of=None):
        as_of = as_of or date.today()
        if not self.api.access_token and not self.api.authorize():
            return [], {"status": "BCS_AUTH_FAILED", "version": self.VERSION}
        self._underlying_day_change_cache = {}
        bcs_contracts = self._active_contracts()
        underlying_quotes = self._underlying_quotes(bcs_contracts)
        marketdata_error = None
        front_contracts = self.oi.marketdata_front_contracts(as_of=as_of) if hasattr(self.oi, "marketdata_front_contracts") else {}
        marketdata_error = getattr(self.oi, "_marketdata_all_error", None)
        if not front_contracts and hasattr(self.oi, "_request_marketdata_family"):
            family_rows = {}
            families = sorted({str(item.get("oi_root") or item.get("futures_root") or "").upper() for item in bcs_contracts if str(item.get("oi_root") or item.get("futures_root") or "").strip()})
            for family in families:
                try:
                    row = self.oi._request_marketdata_family(family)
                except Exception as exc:
                    marketdata_error = f"MOEX_MARKETDATA_FAMILY_ERROR:{type(exc).__name__}"
                    continue
                if isinstance(row, dict):
                    family_rows[family] = row
            if family_rows:
                front_contracts = family_rows
                marketdata_error = None
        if not front_contracts:
            resilient_rows, resilient_error = self._load_marketdata_all_resilient()
            if resilient_rows and hasattr(self.oi, "_front_marketdata_rows"):
                front_contracts = self.oi._front_marketdata_rows(resilient_rows, as_of=as_of)
                marketdata_error = None
            elif resilient_error:
                marketdata_error = resilient_error
        candidates, skipped, oi_available = [], 0, 0
        liquidity_available = 0
        base_change_available = 0
        base_change_source_counts = {}
        turnover_source_counts = {}
        for family, marketdata in sorted(front_contracts.items()):
            secid = self._text(marketdata, "secid", "ticker", "securityCode").upper()
            if not secid:
                skipped += 1; continue
            last = self._float(marketdata, "last", "lastPrice", "price", "currentPrice")
            change = self._float(marketdata, "lastchangeprcnt", "lastChangePrcnt", "lastChangePercent", "lasttoprevprice", "lastToPrevPrice")
            if change is None:
                previous = self._float(marketdata, "prevsettleprice", "prevSettlePrice", "prevprice", "lastSettlPrice")
                if last is not None and previous and previous > 0: change = (last / previous - 1.0) * 100.0
            if bool(marketdata.get("_futoi_fallback")): last, change = 0.0, None
            if last is None: skipped += 1; continue
            volume = self._float(marketdata, "voltoday", "volume", "volumeContracts", "totalVolume")
            turnover_rub = self._session_turnover(marketdata)
            turnover_source = self._session_turnover_source(marketdata)
            turnover_source_counts[turnover_source] = turnover_source_counts.get(turnover_source, 0) + 1
            oi = self.oi._marketdata_analysis(secid, family, change, None)
            if not oi or oi.get("oi_status") not in {"AVAILABLE", "CURRENT_ONLY"}: skipped += 1; continue
            oi_available += 1
            liquidity_available += int(turnover_rub > 0)
            underlying_ticker = self._underlying_family_tickers.get(family) or self._known_underlying_ticker(family, bcs_contracts)
            underlying_quote = underlying_quotes.get(self._underlying_bcs_tickers.get(underlying_ticker, underlying_ticker), {})
            underlying_price = self._float(underlying_quote, "lastPrice", "last", "price", "currentPrice", "close")
            underlying_change, underlying_change_source = self._underlying_day_change(underlying_ticker)
            base_change_source_counts[underlying_change_source] = base_change_source_counts.get(underlying_change_source, 0) + 1
            if underlying_change is not None: base_change_available += 1
            candidates.append({"futures_root": family, "oi_root": family, "futures_ticker": secid, "last": last, "change_pct": change, "change_percent": change, "volume": volume, "turnover_rub": turnover_rub, "turnover_source": turnover_source, "oi": oi, "oi_analysis": oi, "underlying_ticker": underlying_ticker, "underlying_bcs_ticker": self._underlying_bcs_tickers.get(underlying_ticker), "underlying_class_code": self._underlying_class_codes.get(underlying_ticker), "underlying_price": underlying_price, "underlying_change_pct": underlying_change, "underlying_change_source": underlying_change_source})
        candidates.sort(key=lambda row: float(row.get("turnover_rub") or 0.0), reverse=True)
        selected = candidates[:self.LIQUIDITY_TOP_LIMIT]
        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics.update(getattr(self, "_underlying_metadata_diagnostics", {}))
        process_status = "OK" if candidates else ("DEGRADED" if marketdata_error else "NO_DATA")
        underlying_requested = len(self._underlying_family_tickers)
        underlying_class_codes = len(self._underlying_class_codes)
        underlying_class_code_missing = max(0, underlying_requested - underlying_class_codes)
        base_change_total = len(candidates)
        base_change_missing = max(0, base_change_total - base_change_available)
        base_change_coverage = round(base_change_available / base_change_total * 100.0, 2) if base_change_total else 0.0
        underlying_mapping_coverage = round(underlying_class_codes / underlying_requested * 100.0, 2) if underlying_requested else 0.0
        data_quality_issues = []
        if underlying_class_code_missing: data_quality_issues.append("INCOMPLETE_UNDERLYING_MAPPING")
        if base_change_missing: data_quality_issues.append("INCOMPLETE_BASE_CHANGE")
        if marketdata_error: data_quality_issues.append("MARKETDATA_ERROR")
        data_quality_status = "COMPLETE" if not data_quality_issues else "INCOMPLETE"
        diagnostics.update({"status": process_status, "process_status": process_status, "data_quality_status": data_quality_status, "data_quality_issues": data_quality_issues, "underlying_mapping_coverage_percent": underlying_mapping_coverage, "base_change_coverage_percent": base_change_coverage, "version": self.VERSION, "contracts": len(candidates), "analyzed": len(candidates), "returned": len(selected), "oi_available": oi_available, "skipped": skipped, "liquidity_available": liquidity_available, "liquidity_top_limit": self.LIQUIDITY_TOP_LIMIT, "liquidity_top_returned": len(selected), "liquidity_metric": "MOEX_RFUD_CURRENT_DAY_MONETARY_TURNOVER", "turnover_source": "VALTODAY_ONLY", "turnover_source_counts": turnover_source_counts, "base_change_available": base_change_available, "base_change_missing": base_change_missing, "base_change_policy": "BCS_INTRADAY_07:00_NOW", "base_change_interval": self.UNDERLYING_CANDLE_INTERVAL, "base_change_source_counts": base_change_source_counts, "oi_source": "MOEX_FUTURES_MARKETDATA_PRIMARY", "mapping": "MOEX_RFUD_SECID_TO_FAMILY + BCS_UNDERLYING_CONTEXT", "selection_policy": "MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY", "liquidity_policy": "CURRENT_DAY_TURNOVER_DESC_TOP_20; NO_SYNTHETIC_PRICE_X_VOLUME", "marketdata_source": "MOEX_ISS_FUTURES_MARKETDATA", "marketdata_error": marketdata_error})
        self._last_diagnostics = diagnostics
        return selected, diagnostics
