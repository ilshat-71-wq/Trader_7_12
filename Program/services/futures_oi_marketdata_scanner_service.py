from datetime import date, datetime, time, timezone
from math import log1p
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from services.futures_oi_scanner_service import FuturesOIScannerService


class FuturesOIMarketDataScannerService(FuturesOIScannerService):
    """MOEX RFUD futures OI scanner with current-day liquidity TOP."""

    VERSION = "2.7.7"
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
        if getattr(oi_cls, "TIMEOUT", 0) < 15:
            oi_cls.TIMEOUT = 15
        if getattr(oi_cls, "MARKETDATA_RETRIES", 0) < 3:
            oi_cls.MARKETDATA_RETRIES = 3
        self._underlying_class_codes = {}
        self._underlying_day_change_cache = {}

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
        explicit = {"SBRF": "SBER", "SR": "SBER"}
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
        aliases = {"SI": "USDRUB", "EU": "EURRUB", "CR": "CNYRUB", "NA": "QQQ", "SF": "SPYF", "MX": "MIX", "MM": "MXI", "RI": "RTS", "RM": "RTSM", "VI": "RVI"}
        return aliases.get(mapped, mapped)

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

    def _underlying_quotes(self, contracts):
        """Load underlying quotes and retain the actual exchange class code for candles."""
        requested = {}
        for item in contracts:
            ticker = self._text(item, "underlying_ticker", "underlyingTicker", "underlyingSecCode")
            if not ticker:
                continue
            key = ticker.upper()
            requested.setdefault(key, {"ticker": ticker, "classCode": self._text(item, "underlying_class_code", "underlyingClassCode", "underlying_class_code")})

        unresolved = [key for key, item in requested.items() if not item.get("classCode")]
        if unresolved:
            try:
                records = self.api.get_instruments_by_tickers(unresolved)
            except Exception as exc:
                print("⚠️ Underlying metadata lookup failed:", type(exc).__name__)
                records = []
            for record in records if isinstance(records, list) else []:
                ticker = self._text(record, "ticker", "secCode", "securityCode").upper()
                if not ticker or ticker not in requested:
                    continue
                class_code = self._select_underlying_class_code(record)
                if class_code and not requested[ticker].get("classCode"):
                    requested[ticker]["classCode"] = class_code

        self._underlying_class_codes = {key: value.get("classCode") for key, value in requested.items() if value.get("classCode")}
        instruments = [item for item in requested.values() if item.get("classCode")]
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
        class_code = self._underlying_class_codes.get(ticker)
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
            bars = self.api.get_candles(ticker, class_code, interval=self.UNDERLYING_CANDLE_INTERVAL, start_time=start.astimezone(timezone.utc), end_time=now.astimezone(timezone.utc))
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
            first_open = valid[0][1]
            last_close = valid[-1][2]
            result = (round((last_close / first_open - 1.0) * 100.0, 6), "BCS_M5_07:00_NOW")
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
        if not front_contracts:
            resilient_rows, resilient_error = self._load_marketdata_all_resilient()
            if resilient_rows:
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
                skipped += 1
                continue
            last = self._float(marketdata, "last", "lastPrice", "price", "currentPrice")
            change = self._float(marketdata, "lastchangeprcnt", "lastChangePrcnt", "lastChangePercent", "lasttoprevprice", "lastToPrevPrice")
            if change is None:
                previous = self._float(marketdata, "prevsettleprice", "prevSettlePrice", "prevprice", "lastSettlPrice")
                if last is not None and previous and previous > 0:
                    change = (last / previous - 1.0) * 100.0
            if bool(marketdata.get("_futoi_fallback")):
                last, change = 0.0, None
            if last is None:
                skipped += 1
                continue
            volume = self._float(marketdata, "voltoday", "volume", "volumeContracts", "totalVolume")
            turnover_rub = self._session_turnover(marketdata)
            turnover_source = self._session_turnover_source(marketdata)
            turnover_source_counts[turnover_source] = turnover_source_counts.get(turnover_source, 0) + 1
            oi = self.oi._marketdata_analysis(secid, family, change, None)
            if not oi or oi.get("oi_status") not in {"AVAILABLE", "CURRENT_ONLY"}:
                skipped += 1
                continue
            oi_available += 1
            liquidity_available += int(turnover_rub > 0)
            underlying_ticker = self._known_underlying_ticker(family, bcs_contracts)
            underlying_quote = underlying_quotes.get(underlying_ticker, {})
            underlying_price = self._float(underlying_quote, "lastPrice", "last", "price", "currentPrice", "close")
            underlying_change, underlying_change_source = self._underlying_day_change(underlying_ticker)
            base_change_source_counts[underlying_change_source] = base_change_source_counts.get(underlying_change_source, 0) + 1
            if underlying_change is not None:
                base_change_available += 1
            candidates.append({
                "futures_root": family, "oi_root": family, "futures_ticker": secid,
                "futures_ticker_normalized": secid, "futures_class_code": "RFUD", "curve_rank": 1, "curve_role": "FRONT",
                "_expiry": marketdata.get("_moex_expiry") or "9999-99-99", "underlying_ticker": underlying_ticker, "underlying_asset": underlying_ticker,
                "economic_exposure_group": self._economic_exposure_group(family), "price": last, "change_percent": round(change, 4), "volume": volume,
                "session_turnover_rub": round(turnover_rub, 2) if turnover_rub else 0.0, "turnover_source": turnover_source,
                "liquidity_available": bool(turnover_rub > 0), "liquidity_score": self._liquidity_score(turnover_rub, oi.get("oi"), volume),
                "oi_analysis": oi, "underlying_price": underlying_price,
                "underlying_change_percent": None if underlying_change is None else round(underlying_change, 4),
                "underlying_change_source": underlying_change_source,
                "underlying_data_status": "AVAILABLE" if underlying_price is not None else "UNAVAILABLE",
                "direction_alignment": ("ALIGNED_UP" if change is not None and underlying_change is not None and change > 0 and underlying_change > 0 else "ALIGNED_DOWN" if change is not None and underlying_change is not None and change < 0 and underlying_change < 0 else "DIVERGENCE" if change is not None and underlying_change is not None and change * underlying_change < 0 else "NEUTRAL"),
                "data_status": "AVAILABLE",
            })

        candidates.sort(key=lambda x: (float(x.get("session_turnover_rub") or 0.0), float(x.get("liquidity_score") or 0.0), float((x.get("oi_analysis") or {}).get("oi") or 0.0)), reverse=True)
        liquidity_rows = [x for x in candidates if x.get("liquidity_available")]
        liquidity_probe = {}
        for rank, item in enumerate(liquidity_rows, 1):
            root = str(item.get("futures_root") or "").upper()
            if root in self.LIQUIDITY_PROBE_ROOTS:
                liquidity_probe[root] = {"rank": rank, "contract": item.get("futures_ticker"), "turnover_rub": item.get("session_turnover_rub"), "oi": (item.get("oi_analysis") or {}).get("oi")}
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
        status = "OK" if candidates else ("DEGRADED" if marketdata_error else "NO_DATA")
        diagnostics.update({
            "status": status, "version": self.VERSION, "contracts": len(front_contracts), "analyzed": len(candidates), "returned": len(selected), "oi_available": oi_available,
            "skipped": skipped, "quote_instruments": len(underlying_quotes), "quote_records": len(underlying_quotes), "marketdata_oi_records": oi_available,
            "liquidity_available": liquidity_available, "liquidity_top_limit": self.LIQUIDITY_TOP_LIMIT, "liquidity_top_returned": len(selected),
            "liquidity_metric": "MOEX_RFUD_CURRENT_DAY_MONETARY_TURNOVER", "turnover_source": "VALTODAY_ONLY", "turnover_source_counts": turnover_source_counts,
            "liquidity_probe_roots": liquidity_probe, "economic_overlap_groups": economic_overlap,
            "base_change_available": base_change_available, "base_change_missing": max(0, len(candidates) - base_change_available),
            "base_change_policy": "BCS_INTRADAY_07:00_NOW", "base_change_interval": self.UNDERLYING_CANDLE_INTERVAL,
            "base_change_source_counts": base_change_source_counts,
            "oi_source": "MOEX_FUTURES_MARKETDATA_PRIMARY", "mapping": "MOEX_RFUD_SECID_TO_FAMILY + BCS_UNDERLYING_CONTEXT",
            "selection_policy": "MOEX_RFUD_FRONT_NONEXPIRED_NONZERO_OI_PER_FAMILY", "liquidity_policy": "CURRENT_DAY_TURNOVER_DESC_TOP_20; NO_SYNTHETIC_PRICE_X_VOLUME",
            "marketdata_source": "MOEX_ISS_FUTURES_FORTS_RFUD", "marketdata_error": marketdata_error,
        })
        print("Futures OI diagnostics:", diagnostics)
        return selected, diagnostics
