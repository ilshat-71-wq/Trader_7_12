"""
Trader_7_12 Pro

BCS API

Версия 1.0

Назначение:
- авторизация BCS
- инструменты
- котировки
- сделки
- стакан
- свечи

Рыночные данные работают через один process-wide read-only client.
Candle HTTP concurrency ограничена безопасным уровнем ниже лимита BCS
(10 RPS для рыночных данных), чтобы широкий TQBR-скан не сериализовался
одним запросом за раз и не зависал на таймаутах.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import threading
import time

from config import get_refresh_token, save_refresh_token
from api.request_helper import RequestHelper


class BCSAPI:

    CANDLE_CACHE_TTL = 30.0
    CANDLE_TIMEOUT = 8.0
    CANDLE_RETRIES = 1
    CANDLE_MAX_CONCURRENCY = 6
    CANDLE_DIAGNOSTICS = True
    CANDLE_DIAGNOSTIC_EVERY = 50
    METADATA_TIMEOUT = 5.0
    METADATA_RETRIES = 2
    INSTRUMENT_METADATA_PAGE_SIZE = 200
    INSTRUMENT_METADATA_MAX_PAGES = 100
    INSTRUMENT_METADATA_CACHE_TTL = 300.0
    UNDERLYING_LOOKUP_TYPES = (
        "CURRENCY", "STOCK", "FOREIGN_STOCK", "ETF", "GOODS", "INDICES",
    )

    _shared_instance = None
    _initialized = False

    def __new__(cls):
        # Keep the production BCSAPI process-wide singleton, but allow
        # subclasses (including test fakes) to have their own instance.
        # Looking up an inherited _shared_instance would otherwise return
        # the real BCSAPI object and bypass subclass overrides.
        if "_shared_instance" not in cls.__dict__ or cls._shared_instance is None:
            cls._shared_instance = super().__new__(cls)
        return cls._shared_instance

    def __init__(self):
        if self.__class__._initialized:
            return
        self.access_token = None
        self._access_token_expires_at = 0.0
        self._auth_lock = threading.RLock()
        self.info_url = "https://be.broker.ru/trade-api-information-service/api/v1"
        self.market_url = "https://be.broker.ru/trade-api-market-data-connector/api/v1"
        self._candle_cache = {}
        self._instrument_metadata_cache = {}
        self._underlying_metadata_index_cache = {}
        self._ticker_metadata_cache = {}
        self._ticker_metadata_record_cache = {}
        self._candle_diag_lock = threading.RLock()
        self._candle_diag = {
            "M5": {"requests": 0, "cache_hits": 0, "cache_misses": 0, "http_ok": 0, "http_errors": 0, "http_seconds": 0.0, "http_statuses": {}, "exceptions": {}, "first_error": None, "last_error": None},
            "D": {"requests": 0, "cache_hits": 0, "cache_misses": 0, "http_ok": 0, "http_errors": 0, "http_seconds": 0.0, "http_statuses": {}, "exceptions": {}, "first_error": None, "last_error": None},
        }
        self._candle_semaphore = threading.Semaphore(self.CANDLE_MAX_CONCURRENCY)
        self.__class__._initialized = True

    def authorize(self, force=False):
        """Ensure a valid BCS read-only access token is available."""
        now = time.time()
        if (
            not force
            and self.access_token
            and now < self._access_token_expires_at - 60
        ):
            return True

        with self._auth_lock:
            now = time.time()
            if (
                not force
                and self.access_token
                and now < self._access_token_expires_at - 60
            ):
                return True

            refresh_token = get_refresh_token()
            if not refresh_token:
                print("❌ BCS refresh token is not configured")
                return False

            url = (
                "https://be.broker.ru/trade-api-keycloak/"
                "realms/tradeapi/protocol/openid-connect/token"
            )
            payload = {
                "client_id": "trade-api-read",
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }

            r = RequestHelper.post(url, data=payload)

            if r.status_code == 200:
                data = r.json()
                access_token = data.get("access_token")
                if not access_token:
                    print("❌ BCS authorization response has no access_token")
                    return False

                self.access_token = access_token
                expires_in = float(data.get("expires_in") or 86400)
                self._access_token_expires_at = time.time() + expires_in

                rotated_token = data.get("refresh_token")
                if rotated_token:
                    save_refresh_token(rotated_token)

                print("✅ Авторизация БКС успешна")
                return True

            print("❌ BCS authorization HTTP:", r.status_code)
            return False

    def headers(self):
        if not self.authorize():
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_instruments(self, instrument_type="FUTURES"):
        """Load instrument metadata with bounded pagination, loop protection and a short cache."""
        instrument_type = str(instrument_type or "FUTURES").strip().upper()
        if not instrument_type:
            return []

        now = time.time()
        cached = self._instrument_metadata_cache.get(instrument_type)
        if cached is not None:
            cached_at, cached_records = cached
            if now - cached_at < self.INSTRUMENT_METADATA_CACHE_TTL:
                return list(cached_records)

        url = f"{self.info_url}/instruments/by-type"
        result = []
        seen_page_signatures = set()
        server_page_size = None

        for page in range(self.INSTRUMENT_METADATA_MAX_PAGES):
            params = {
                "type": instrument_type,
                "page": page,
                "size": self.INSTRUMENT_METADATA_PAGE_SIZE,
            }
            r = RequestHelper.get(
                url,
                headers=self.headers(),
                params=params,
                timeout=self.METADATA_TIMEOUT,
                max_retries=self.METADATA_RETRIES,
            )
            print(f"Instruments page {page}:", r.status_code)
            if r.status_code != 200:
                break

            try:
                data = r.json()
            except ValueError:
                print("⚠️ Instruments JSON parse failed:", instrument_type, page)
                break

            records = (
                data
                if isinstance(data, list)
                else data.get("instruments", data.get("records", []))
            )
            if not isinstance(records, list) or not records:
                break

            signature = tuple(
                (
                    str(
                        record.get("ticker")
                        or record.get("secCode")
                        or record.get("securityCode")
                        or ""
                    ).upper(),
                    str(record.get("isin") or "").upper(),
                    str(record.get("classCode") or record.get("class_code") or ""),
                )
                for record in records
                if isinstance(record, dict)
            )
            if signature in seen_page_signatures:
                print("⚠️ Instruments pagination repeated page:", instrument_type, page)
                break
            seen_page_signatures.add(signature)

            result.extend(record for record in records if isinstance(record, dict))

            # BCS may return a fixed server-side page size different
            # from the requested size. Learn that size from the first
            # non-empty page, then use it to detect the final page.
            if server_page_size is None:
                server_page_size = len(records)
            if len(records) < server_page_size:
                break

        else:
            print(
                "⚠️ Instruments pagination reached safety limit:",
                instrument_type,
                self.INSTRUMENT_METADATA_MAX_PAGES,
            )

        self._instrument_metadata_cache[instrument_type] = (now, list(result))
        print("Всего загружено:", len(result))
        return result

    @staticmethod
    def _instrument_lookup_key(value):
        """Normalize only unambiguous ticker spelling variants for metadata lookup."""
        value = str(value or "").strip().upper()
        if not value:
            return ""
        value = value.replace("/", "").replace("-", "").replace("_", "")
        for suffix in ("TOM", "F"):
            if value.endswith(suffix) and len(value) > len(suffix):
                value = value[:-len(suffix)]
                break
        return value

    @staticmethod
    def _record_class_code(record):
        if not isinstance(record, dict):
            return ""
        direct = str(record.get("classCode") or record.get("class_code") or record.get("classcode") or "").strip()
        if direct:
            return direct
        fallback = str(record.get("_underlying_bcs_class_code") or "").strip()
        if fallback:
            return fallback
        boards = record.get("boards")
        if isinstance(boards, dict):
            boards = [boards]
        for board in boards or []:
            if not isinstance(board, dict):
                continue
            code = str(board.get("classCode") or board.get("class_code") or board.get("classcode") or "").strip()
            if code:
                return code
        return ""

    @classmethod
    def _record_aliases(cls, record):
        """Return all real BCS metadata aliases that can identify an economic underlying."""
        if not isinstance(record, dict):
            return set()

        fields = (
            "ticker", "secCode", "securityCode", "baseAssetTicker", "base_asset_ticker",
            "underlyingAsset", "underlying_asset", "underlying", "underlyingTicker",
            "underlying_ticker", "underlyingSecCode", "underlying_sec_code", "assetCode",
            "asset_code", "baseAsset", "base_asset", "baseTicker", "base_ticker",
            "shortCode", "short_code",
        )

        result = set()
        for field in fields:
            value = record.get(field)
            if value:
                key = cls._instrument_lookup_key(value)
                if key:
                    result.add(key)

        # BCS exposes MIX, MXI and IMOEXF as separate FUTURES instruments,
        # while their common economic base asset is the real IMOEX index.
        # When the fallback is scanning real INDICES metadata, map those
        # futures aliases to the actual IMOEX record instead of accepting a
        # derivative as the underlying.
        if "IMOEX" in result:
            result.update({"MIX", "MXI", "IMOEXF", "MX", "MM"})
        if "RTS" in result:
            result.update({"RTSM", "RI", "RM"})
        if "RVI" in result:
            result.add("VI")
        return result

    def _underlying_metadata_fallback(self, requested, existing):
        """Resolve real non-futures underlyings from BCS by-type metadata."""
        unresolved = set()
        for ticker in requested:
            key = self._instrument_lookup_key(ticker)
            if key:
                # Canonicalize real BCS spelling variants before fallback.
                # Example: USDRUB_TOM -> USDRUB. This lets the live
                # by-type directory match a currency record even when the
                # initial by-tickers lookup returned an incomplete card.
                unresolved.add(key)
        for record in existing:
            if not isinstance(record, dict):
                continue
            if self._record_class_code(record):
                unresolved.difference_update(self._record_aliases(record))
        if not unresolved:
            return existing, {"fallback_types": [], "fallback_records": 0, "fallback_matches": 0, "fallback_unresolved": 0}

        result = list(existing)
        seen = {
            (
                self._instrument_lookup_key(record.get("ticker") or record.get("secCode") or record.get("securityCode")),
                self._record_class_code(record).upper(),
            )
            for record in result if isinstance(record, dict)
        }
        fallback_types = []
        fallback_records = 0
        fallback_matches = 0
        fallback_index_hits = 0
        now = time.time()

        for instrument_type in self.UNDERLYING_LOOKUP_TYPES:
            if not unresolved:
                break

            try:
                index_cache = getattr(self, "_underlying_metadata_index_cache", None)
                if index_cache is None:
                    index_cache = {}
                    self._underlying_metadata_index_cache = index_cache
                cached_index = index_cache.get(instrument_type)
                if (
                    cached_index is not None
                    and now - cached_index[0] < self.INSTRUMENT_METADATA_CACHE_TTL
                ):
                    index, record_count = cached_index[1], cached_index[2]
                    fallback_index_hits += 1
                else:
                    records = self.get_instruments(instrument_type)
                    if not isinstance(records, list):
                        records = []
                    index = {}
                    for record in records:
                        if not isinstance(record, dict):
                            continue
                        for alias in self._record_aliases(record):
                            index.setdefault(alias, []).append(record)
                    index_cache[instrument_type] = (
                        now,
                        index,
                        len(records),
                    )
                    record_count = len(records)
                fallback_types.append(instrument_type)
                fallback_records += record_count

            except Exception as exc:
                print("⚠️ Underlying by-type lookup failed:", instrument_type, type(exc).__name__)
                continue

            for requested_key in list(unresolved):
                for record in index.get(requested_key, []):
                    if not isinstance(record, dict):
                        continue

                    class_code = self._record_class_code(record)
                    if not class_code:
                        continue

                    actual_ticker = str(
                        record.get("ticker") or record.get("secCode") or record.get("securityCode") or ""
                    ).strip().upper()

                    matched_aliases = sorted(
                        self._record_aliases(record).intersection(unresolved)
                    )
                    if requested_key not in matched_aliases:
                        matched_aliases.append(requested_key)
                        matched_aliases = sorted(set(matched_aliases))

                    enriched = dict(record)
                    enriched["_underlying_requested_aliases"] = matched_aliases
                    enriched["_underlying_bcs_ticker"] = actual_ticker
                    enriched["_underlying_bcs_class_code"] = class_code
                    enriched["_underlying_mapping_source"] = "BCS_BY_TYPE_METADATA"

                    dedupe_key = (actual_ticker or "|".join(matched_aliases), class_code.upper())
                    if dedupe_key not in seen:
                        result.append(enriched)
                        seen.add(dedupe_key)
                        fallback_matches += 1

                    for key in matched_aliases:
                        unresolved.discard(key)

        return result, {
            "fallback_types": fallback_types,
            "fallback_records": fallback_records,
            "fallback_matches": fallback_matches,
            "fallback_index_hits": fallback_index_hits,
            "fallback_unresolved": len(unresolved),
        }

    def get_instruments_by_tickers(self, tickers, resolve_underlying=True):
        """Load BCS instrument cards with exact-set and per-ticker metadata caches."""
        if not isinstance(tickers, (list, tuple)):
            return []
        requested = [str(t).strip().upper() for t in tickers if str(t).strip()]
        if not requested:
            return []

        resolve_key = bool(resolve_underlying)
        unique_requested = sorted(set(requested))
        ticker_cache_key = (tuple(unique_requested), resolve_key)
        now = time.time()

        # Fast path for an exact repeated request.
        cached_tickers = self._ticker_metadata_cache.get(ticker_cache_key)
        if cached_tickers is not None:
            cached_at, cached_records = cached_tickers
            if now - cached_at < self.INSTRUMENT_METADATA_CACHE_TTL:
                return [dict(record) for record in cached_records]
            self._ticker_metadata_cache.pop(ticker_cache_key, None)

        # Main deduplication path: reuse already-known BCS cards even when
        # the next caller asks for a different, overlapping ticker set.
        record_cache = getattr(self, "_ticker_metadata_record_cache", None)
        if record_cache is None:
            record_cache = {}
            self._ticker_metadata_record_cache = record_cache

        cached_records = {}
        missing = []
        for ticker in unique_requested:
            key = self._instrument_lookup_key(ticker)
            cached = record_cache.get((key, resolve_key)) if key else None
            if cached is not None:
                cached_at, record = cached
                if now - cached_at < self.INSTRUMENT_METADATA_CACHE_TTL:
                    cached_records[ticker] = dict(record)
                    continue
                record_cache.pop((key, resolve_key), None)
            missing.append(ticker)

        fetched_records = []
        if missing:
            url = f"{self.info_url}/instruments/by-tickers"
            seen_page_signatures = set()
            page = 0
            page_size = 100
            max_pages = 20
            while page < max_pages:
                payload = {"tickers": missing, "page": page, "size": page_size}
                try:
                    r = RequestHelper.post(
                        url,
                        headers={**self.headers(), "Content-Type": "application/json"},
                        json=payload,
                    )
                except Exception as exc:
                    print("Instrument ticker lookup failed:", type(exc).__name__)
                    break
                print(f"Instrument ticker lookup page {page}:", r.status_code)
                if r.status_code != 200:
                    break
                try:
                    data = r.json()
                except ValueError:
                    break
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    records = data.get("instruments", data.get("records", []))
                else:
                    records = []
                if not isinstance(records, list) or not records:
                    break
                signature = tuple(
                    (
                        str(
                            record.get("ticker")
                            or record.get("secCode")
                            or record.get("securityCode")
                            or ""
                        ).upper(),
                        str(record.get("isin") or "").upper(),
                        str(record.get("classCode") or ""),
                        str(record.get("class_code") or ""),
                    )
                    for record in records
                    if isinstance(record, dict)
                )
                if signature in seen_page_signatures:
                    break
                seen_page_signatures.add(signature)
                fetched_records.extend(
                    record for record in records if isinstance(record, dict)
                )
                if len(records) < page_size:
                    break
                page += 1

        all_records = list(cached_records.values()) + fetched_records

        # Underlying fallback is still the single source of enrichment. It
        # runs only against the requested set, while the per-ticker cache
        # prevents repeated /by-tickers HTTP calls across overlapping sets.
        if resolve_underlying:
            all_records, fallback_diag = self._underlying_metadata_fallback(
                unique_requested, all_records
            )
            if fallback_diag.get("fallback_matches"):
                print("Underlying metadata fallback:", fallback_diag)

        # Cache each returned real BCS record under every unambiguous alias
        # that identifies it. This is what makes overlapping requests cheap.
        for record in all_records:
            if not isinstance(record, dict):
                continue
            aliases = self._record_aliases(record)
            aliases.add(
                self._instrument_lookup_key(
                    record.get("ticker")
                    or record.get("secCode")
                    or record.get("securityCode")
                )
            )
            for alias in aliases:
                if alias:
                    record_cache[(alias, resolve_key)] = (now, dict(record))

        self._ticker_metadata_cache[ticker_cache_key] = (now, list(all_records))
        return [dict(record) for record in all_records]

    def get_quotes(self, instruments):
        url = f"{self.market_url}/quotes"
        payload = {"instruments": instruments}
        r = RequestHelper.post(url, headers={**self.headers(), "Content-Type": "application/json"}, json=payload)
        print("Quotes:", r.status_code)
        if r.status_code == 200:
            return r.json()
        return {}

    def get_quotes_batch(self, instruments):
        result = []
        batch_size = 100
        for i in range(0, len(instruments), batch_size):
            batch = instruments[i:i + batch_size]
            print("📊 Quotes batch", i // batch_size + 1, len(batch))
            data = self.get_quotes(batch)
            result.extend(data.get("records", []))
        return result

    def get_last_trades(self, ticker, class_code):
        url = f"{self.market_url}/last-trades"
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=30)
        payload = {"ticker": ticker, "classCode": class_code, "startDateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "endDateTime": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
        try:
            r = RequestHelper.post(url, headers={**self.headers(), "Content-Type": "application/json"}, json=payload)
        except Exception as exc:
            print("⚠️ Trades request failed:", ticker, class_code, type(exc).__name__, str(exc))
            return {"records": []}
        if r.status_code != 200:
            print("⚠️ Trades HTTP:", ticker, class_code, r.status_code, r.text[:300])
            return {"records": []}
        try:
            data = r.json()
        except ValueError:
            print("⚠️ Trades JSON parse failed:", ticker, class_code)
            return {"records": []}
        records = data.get("records", [])
        if not isinstance(records, list):
            records = []
        records.sort(key=lambda x: x.get("dateTime", x.get("time", "")))
        print("TRADES COLLECTED:", ticker, class_code, len(records))
        if records:
            print("FIRST TRADE:", records[0].get("dateTime", records[0].get("time")), records[0].get("price"))
            print("LAST TRADE:", records[-1].get("dateTime", records[-1].get("time")), records[-1].get("price"))
        return {"records": records}

    def get_order_book(self, ticker, class_code):
        """Load the current Level-2 book through BCS's documented GET endpoint."""
        url = f"{self.market_url}/order-book"
        params = {"ticker": ticker, "classCode": class_code, "depth": 10}
        try:
            r = RequestHelper.get(url, headers=self.headers(), params=params, timeout=self.METADATA_TIMEOUT, max_retries=self.METADATA_RETRIES)
        except Exception as exc:
            print("⚠️ Order-book request failed:", ticker, class_code, type(exc).__name__)
            return {}
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                print("⚠️ Order-book JSON parse failed:", ticker, class_code)
                return {}
        print("⚠️ Order-book HTTP:", ticker, class_code, r.status_code)
        return {}

    @staticmethod
    def _candle_cache_key(ticker, class_code, interval, start_dt, end_dt):
        interval_key = str(interval).upper()
        if interval_key == "M5":
            moscow_date = start_dt.astimezone(ZoneInfo("Europe/Moscow")).date()
            return (
                str(ticker).upper(),
                str(class_code),
                interval_key,
                moscow_date.isoformat(),
            )
        start_key = start_dt.replace(second=0, microsecond=0).isoformat()
        end_key = end_dt.replace(second=0, microsecond=0).isoformat()
        return (
            str(ticker).upper(),
            str(class_code),
            interval_key,
            start_key,
            end_key,
        )

    @staticmethod
    def _candle_record_datetime(record):
        if not isinstance(record, dict):
            return None

        value = (
            record.get("dateTime")
            or record.get("datetime")
            or record.get("date")
            or record.get("time")
            or record.get("timestamp")
        )
        if value is None:
            return None

        try:
            if isinstance(value, datetime):
                dt = value
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(
                    value / 1000.0 if value > 10_000_000_000 else value,
                    tz=timezone.utc,
                )
            else:
                text = str(value).strip()
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                dt = datetime.fromisoformat(text)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    @classmethod
    def _slice_candle_data(cls, data, start_dt, end_dt):
        if not isinstance(data, dict):
            return data

        records = data.get("records")
        if not isinstance(records, list):
            return data

        filtered = []
        for record in records:
            dt = cls._candle_record_datetime(record)
            if dt is None or start_dt <= dt < end_dt:
                filtered.append(record)

        result = dict(data)
        result["records"] = filtered
        return result

    def _print_candle_diagnostic(self, interval_key, diag):
        if not self.CANDLE_DIAGNOSTICS:
            return
        requests = int(diag.get("requests", 0))
        if requests <= 0 or requests % self.CANDLE_DIAGNOSTIC_EVERY != 0:
            return
        print(
            f"CANDLE DIAGNOSTICS {interval_key}: "
            f"requests={requests} "
            f"cache_hits={int(diag.get('cache_hits', 0))} "
            f"cache_misses={int(diag.get('cache_misses', 0))} "
            f"http_ok={int(diag.get('http_ok', 0))} "
            f"http_errors={int(diag.get('http_errors', 0))} "
            f"http_seconds={diag.get('http_seconds', 0.0):.3f} "
            f"http_statuses={diag.get('http_statuses', {})} "
            f"exceptions={diag.get('exceptions', {})} "
            f"first_error={diag.get('first_error')} "
            f"last_error={diag.get('last_error')}"
        )

    def get_candle_diagnostics(self):
        with self._candle_diag_lock:
            return {
                key: dict(value)
                for key, value in self._candle_diag.items()
            }

    def get_candles(self, ticker, class_code, interval="M5", start_time=None, end_time=None):
        """Load BCS candles with bounded retry, cache and safe concurrency."""
        url = f"{self.market_url}/candles-chart"
        def normalize_time(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                dt = value
            else:
                text = str(value).strip()
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        try:
            end_dt = normalize_time(end_time) if end_time is not None else now
            if start_time is not None:
                start_dt = normalize_time(start_time)
            elif interval == "D":
                start_dt = end_dt - timedelta(days=30)
            else:
                start_dt = end_dt - timedelta(hours=4)
        except (TypeError, ValueError) as exc:
            print("❌ Invalid candle time:", exc)
            return {}
        if start_dt is None or end_dt is None or start_dt >= end_dt:
            print("❌ Invalid candle period")
            return {}
        interval_key = str(interval).upper()
        cache_key = self._candle_cache_key(ticker, class_code, interval_key, start_dt, end_dt)

        cached = self._candle_cache.get(cache_key)
        if cached is None and interval_key in self._candle_diag:
            with self._candle_diag_lock:
                self._candle_diag[interval_key]["cache_misses"] += 1
        if cached is not None:
            cached_at, cached_data, cached_start, cached_end = cached
            if (now - cached_at).total_seconds() < self.CANDLE_CACHE_TTL:
                if interval_key != "M5" or (cached_start <= start_dt and end_dt <= cached_end):
                    return self._slice_candle_data(cached_data, start_dt, end_dt)

            self._candle_cache.pop(cache_key, None)

        request_start = start_dt
        request_end = end_dt

        if interval_key == "M5":
            moscow_tz = ZoneInfo("Europe/Moscow")
            trading_date = start_dt.astimezone(moscow_tz).date()
            session_start_msk = datetime(
                trading_date.year,
                trading_date.month,
                trading_date.day,
                7, 0, 0,
                tzinfo=moscow_tz,
            )
            session_end_msk = datetime(
                trading_date.year,
                trading_date.month,
                trading_date.day,
                23, 59, 59,
                tzinfo=moscow_tz,
            )
            request_start = session_start_msk.astimezone(timezone.utc)
            request_end = session_end_msk.astimezone(timezone.utc)

        params = {
            "ticker": ticker,
            "classCode": class_code,
            "startDate": request_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": request_end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "timeFrame": interval_key,
        }
        http_started = time.perf_counter()
        try:
            with self._candle_semaphore:
                r = RequestHelper.get(url, headers=self.headers(), params=params, timeout=self.CANDLE_TIMEOUT, max_retries=self.CANDLE_RETRIES)
        except Exception as exc:
            elapsed = time.perf_counter() - http_started
            if interval_key in self._candle_diag:
                with self._candle_diag_lock:
                    diag = self._candle_diag[interval_key]
                    diag["requests"] += 1
                    diag["http_errors"] += 1
                    diag["http_seconds"] += elapsed
                    exception_name = type(exc).__name__
                    diag["exceptions"][exception_name] = diag["exceptions"].get(exception_name, 0) + 1
                    error = {"ticker": str(ticker), "class_code": str(class_code), "interval": interval_key, "type": exception_name, "message": str(exc)[:300]}
                    if diag["first_error"] is None:
                        diag["first_error"] = error
                    diag["last_error"] = error
                    self._print_candle_diagnostic(interval_key, diag)
            print("⚠️ Candle request failed:", ticker, interval, type(exc).__name__)
            return {}
        elapsed = time.perf_counter() - http_started
        if interval_key in self._candle_diag:
            with self._candle_diag_lock:
                diag = self._candle_diag[interval_key]
                diag["requests"] += 1
                diag["http_seconds"] += elapsed
                if r.status_code == 200:
                    diag["http_ok"] += 1
                else:
                    diag["http_errors"] += 1
                    status = str(r.status_code)
                    diag["http_statuses"][status] = diag["http_statuses"].get(status, 0) + 1
                    error = {"ticker": str(ticker), "class_code": str(class_code), "interval": interval_key, "status": r.status_code}
                    if diag["first_error"] is None:
                        diag["first_error"] = error
                    diag["last_error"] = error
                self._print_candle_diagnostic(interval_key, diag)
        if r.status_code != 200:
            print("⚠️ Candle HTTP:", ticker, interval, r.status_code)
            return {}
        try:
            data = r.json()
        except ValueError:
            print("❌ Candles JSON error:", ticker, interval)
            return {}
        self._candle_cache[cache_key] = (
            now,
            data,
            request_start,
            request_end,
        )
        return self._slice_candle_data(data, start_dt, end_dt)

    def get_trades_period(self, ticker, class_code, start_time, end_time):
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = []
        current = start
        while current < end:
            chunk_end = min(current + timedelta(hours=1), end)
            payload = {"ticker": ticker, "classCode": class_code, "startDateTime": current.isoformat(), "endDateTime": chunk_end.isoformat()}
            print("\nPERIOD TRADES PAYLOAD:")
            print(payload)
            r = RequestHelper.post(f"{self.market_url}/last-trades", headers={**self.headers(), "Content-Type": "application/json"}, json=payload)
            print("Period trades status:", r.status_code)
            if r.status_code == 200:
                data = r.json()
                chunk_records = data.get("records", [])
                records.extend(chunk_records)
                print("Chunk records:", len(chunk_records))
            else:
                print("Period trades raw:", r.text[:500])
            current = chunk_end
        return {"records": records}
