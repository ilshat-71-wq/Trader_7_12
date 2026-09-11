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
import threading

from config import get_refresh_token, save_refresh_token
from api.request_helper import RequestHelper


class BCSAPI:

    CANDLE_CACHE_TTL = 30.0
    CANDLE_TIMEOUT = 8.0
    CANDLE_RETRIES = 1
    CANDLE_MAX_CONCURRENCY = 4
    METADATA_TIMEOUT = 5.0
    METADATA_RETRIES = 2
    UNDERLYING_LOOKUP_TYPES = (
        "CURRENCY", "STOCK", "FOREIGN_STOCK", "ETF", "GOODS", "INDICES",
    )

    _shared_instance = None
    _initialized = False

    def __new__(cls):
        if cls._shared_instance is None:
            cls._shared_instance = super().__new__(cls)
        return cls._shared_instance

    def __init__(self):
        if self.__class__._initialized:
            return
        self.access_token = None
        self.info_url = "https://be.broker.ru/trade-api-information-service/api/v1"
        self.market_url = "https://be.broker.ru/trade-api-market-data-connector/api/v1"
        self._candle_cache = {}
        self._candle_semaphore = threading.Semaphore(self.CANDLE_MAX_CONCURRENCY)
        self.__class__._initialized = True

    def authorize(self):
        if self.access_token:
            return True
        refresh_token = get_refresh_token()
        if not refresh_token:
            print("❌ BCS refresh token is not configured")
            return False
        url = "https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token"
        payload = {"client_id": "trade-api-read", "grant_type": "refresh_token", "refresh_token": refresh_token}
        r = RequestHelper.post(url, data=payload)
        if r.status_code == 200:
            data = r.json()
            self.access_token = data.get("access_token")
            rotated_token = data.get("refresh_token")
            if rotated_token:
                save_refresh_token(rotated_token)
            print("✅ Авторизация БКС успешна")
            return bool(self.access_token)
        print(r.text)
        return False

    def headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_instruments(self, instrument_type="FUTURES"):
        """Load instrument metadata with a bounded, metadata-specific retry policy."""
        url = f"{self.info_url}/instruments/by-type"
        result = []
        page = 0
        while True:
            params = {"type": instrument_type, "page": page, "size": 100}
            r = RequestHelper.get(url, headers=self.headers(), params=params, timeout=self.METADATA_TIMEOUT, max_retries=self.METADATA_RETRIES)
            print(f"Instruments page {page}:", r.status_code)
            if r.status_code != 200:
                break
            data = r.json()
            records = data if isinstance(data, list) else data.get("records", [])
            if not records:
                break
            result.extend(records)
            if len(records) < 100:
                break
            page += 1
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
            "ticker",
            "secCode",
            "securityCode",
            "baseAssetTicker",
            "base_asset_ticker",
            "underlyingAsset",
            "underlying_asset",
            "underlying",
            "underlyingTicker",
            "underlying_ticker",
            "underlyingSecCode",
            "underlying_sec_code",
            "assetCode",
            "asset_code",
            "baseAsset",
            "base_asset",
            "baseTicker",
            "base_ticker",
            "shortCode",
            "short_code",
        )

        result = set()
        for field in fields:
            value = record.get(field)
            if value:
                key = cls._instrument_lookup_key(value)
                if key:
                    result.add(key)
        return result

    def _underlying_metadata_fallback(self, requested, existing):
        """Resolve real non-futures underlyings from BCS by-type metadata."""
        unresolved = set()
        for ticker in requested:
            key = self._instrument_lookup_key(ticker)
            if key:
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
        for instrument_type in self.UNDERLYING_LOOKUP_TYPES:
            try:
                records = self.get_instruments(instrument_type)
            except Exception as exc:
                print("⚠️ Underlying by-type lookup failed:", instrument_type, type(exc).__name__)
                continue
            fallback_types.append(instrument_type)
            fallback_records += len(records) if isinstance(records, list) else 0
            for record in records if isinstance(records, list) else []:
                if not isinstance(record, dict):
                    continue

                aliases = self._record_aliases(record)
                matched = sorted(aliases.intersection(unresolved))
                if not matched:
                    continue

                class_code = self._record_class_code(record)
                if not class_code:
                    continue

                actual_ticker = str(
                    record.get("ticker")
                    or record.get("secCode")
                    or record.get("securityCode")
                    or ""
                ).strip().upper()

                # Preserve the real BCS instrument identity. These fields are
                # internal provenance only and never alter the source data.
                enriched = dict(record)
                enriched["_underlying_requested_aliases"] = matched
                enriched["_underlying_bcs_ticker"] = actual_ticker
                enriched["_underlying_bcs_class_code"] = class_code
                enriched["_underlying_mapping_source"] = "BCS_BY_TYPE_METADATA"

                dedupe_key = (
                    actual_ticker or "|".join(matched),
                    class_code.upper(),
                )
                if dedupe_key not in seen:
                    result.append(enriched)
                    seen.add(dedupe_key)
                    fallback_matches += 1

                for key in matched:
                    unresolved.discard(key)
            if not unresolved:
                break
        return result, {
            "fallback_types": fallback_types,
            "fallback_records": fallback_records,
            "fallback_matches": fallback_matches,
            "fallback_unresolved": len(unresolved),
        }

    def get_instruments_by_tickers(self, tickers):
        """Load BCS instrument cards and fill missing classCode from real spot/base metadata."""
        if not isinstance(tickers, (list, tuple)):
            return []
        requested = [str(t).strip().upper() for t in tickers if str(t).strip()]
        if not requested:
            return []
        url = f"{self.info_url}/instruments/by-tickers"
        all_records = []
        seen_page_signatures = set()
        page = 0
        page_size = 100
        max_pages = 20
        while page < max_pages:
            payload = {"tickers": requested, "page": page, "size": page_size}
            try:
                r = RequestHelper.post(url, headers={**self.headers(), "Content-Type": "application/json"}, json=payload)
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
            signature = tuple((str(record.get("ticker") or record.get("secCode") or record.get("securityCode") or "").upper(), str(record.get("isin") or "").upper(), str(record.get("classCode") or ""), str(record.get("class_code") or "")) for record in records if isinstance(record, dict))
            if signature in seen_page_signatures:
                break
            seen_page_signatures.add(signature)
            all_records.extend(record for record in records if isinstance(record, dict))
            if len(records) < page_size:
                break
            page += 1
        all_records, fallback_diag = self._underlying_metadata_fallback(requested, all_records)
        if fallback_diag.get("fallback_matches"):
            print("Underlying metadata fallback:", fallback_diag)
        return all_records

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
        start_key = start_dt.replace(second=0, microsecond=0).isoformat()
        end_key = end_dt.replace(second=0, microsecond=0).isoformat()
        return (str(ticker).upper(), str(class_code), str(interval).upper(), start_key, end_key)

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
        cache_key = self._candle_cache_key(ticker, class_code, interval, start_dt, end_dt)
        cached = self._candle_cache.get(cache_key)
        if cached is not None:
            cached_at, cached_data = cached
            if (now - cached_at).total_seconds() < self.CANDLE_CACHE_TTL:
                return cached_data
            self._candle_cache.pop(cache_key, None)
        params = {"ticker": ticker, "classCode": class_code, "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "timeFrame": interval}
        try:
            with self._candle_semaphore:
                r = RequestHelper.get(url, headers=self.headers(), params=params, timeout=self.CANDLE_TIMEOUT, max_retries=self.CANDLE_RETRIES)
        except Exception as exc:
            print("⚠️ Candle request failed:", ticker, interval, type(exc).__name__)
            return {}
        if r.status_code != 200:
            print("⚠️ Candle HTTP:", ticker, interval, r.status_code)
            return {}
        try:
            data = r.json()
        except ValueError:
            print("❌ Candles JSON error:", ticker, interval)
            return {}
        self._candle_cache[cache_key] = (now, data)
        return data

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