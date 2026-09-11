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

    # BCS documents 10 RPS for market-data HTTP. Keep a small concurrent
    # worker pool so the scanner can use the available throughput without
    # hammering the endpoint.
    CANDLE_CACHE_TTL = 30.0
    CANDLE_TIMEOUT = 8.0
    CANDLE_RETRIES = 1
    CANDLE_MAX_CONCURRENCY = 4
    METADATA_TIMEOUT = 5.0
    METADATA_RETRIES = 2
    TICKER_LOOKUP_BATCH_SIZE = 20

    _shared_instance = None
    _initialized = False

    def __new__(cls):
        """Return one process-wide read-only market-data client."""
        if cls._shared_instance is None:
            cls._shared_instance = super().__new__(cls)
        return cls._shared_instance

    def __init__(self):
        if self.__class__._initialized:
            return

        self.access_token = None
        self.info_url = (
            "https://be.broker.ru/"
            "trade-api-information-service/api/v1"
        )
        self.market_url = (
            "https://be.broker.ru/"
            "trade-api-market-data-connector/api/v1"
        )
        self._candle_cache = {}
        self._candle_semaphore = threading.Semaphore(self.CANDLE_MAX_CONCURRENCY)
        self.__class__._initialized = True

    # ---------------------------------------------------------

    def authorize(self):
        if self.access_token:
            return True

        refresh_token = get_refresh_token()
        if not refresh_token:
            print("❌ BCS refresh token is not configured")
            return False

        url = (
            "https://be.broker.ru/"
            "trade-api-keycloak/"
            "realms/tradeapi/"
            "protocol/openid-connect/token"
        )
        payload = {
            "client_id": "trade-api-read",
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
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

    # ---------------------------------------------------------

    def headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    # ---------------------------------------------------------

    def get_instruments(self, instrument_type="FUTURES"):
        """Load instrument metadata with a bounded, metadata-specific retry policy."""
        url = f"{self.info_url}/instruments/by-type"
        result = []
        page = 0
        while True:
            params = {"type": instrument_type, "page": page, "size": 100}
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

    # ---------------------------------------------------------

    def get_instruments_by_tickers(self, tickers):
        """Load all BCS instrument cards for the requested tickers.

        BCS documents pagination for this endpoint. In practice the server
        may also apply a request-side limit to the ticker filter, so a large
        caller batch must not be treated as one atomic lookup. Split the
        request into small deterministic batches, then paginate each response.
        """
        if not isinstance(tickers, (list, tuple)):
            return []
        requested = []
        seen_requested = set()
        for value in tickers:
            ticker = str(value).strip().upper()
            if ticker and ticker not in seen_requested:
                seen_requested.add(ticker)
                requested.append(ticker)
        if not requested:
            return []

        url = f"{self.info_url}/instruments/by-tickers"
        all_records = []
        seen_records = set()
        batch_size = self.TICKER_LOOKUP_BATCH_SIZE

        for batch_start in range(0, len(requested), batch_size):
            batch = requested[batch_start:batch_start + batch_size]
            seen_page_signatures = set()
            page = 0
            page_size = 100
            max_pages = 20

            while page < max_pages:
                payload = {"tickers": batch, "page": page, "size": page_size}
                try:
                    r = RequestHelper.post(
                        url,
                        headers={**self.headers(), "Content-Type": "application/json"},
                        json=payload
                    )
                except Exception as exc:
                    print("Instrument ticker lookup failed:", type(exc).__name__)
                    break

                print(
                    f"Instrument ticker lookup batch {batch_start // batch_size + 1} "
                    f"({len(batch)}) page {page}: {r.status_code}"
                )
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
                        str(record.get("ticker") or record.get("secCode") or record.get("securityCode") or "").upper(),
                        str(record.get("isin") or "").upper(),
                        str(record.get("classCode") or ""),
                        str(record.get("class_code") or ""),
                    )
                    for record in records if isinstance(record, dict)
                )
                if signature in seen_page_signatures:
                    break
                seen_page_signatures.add(signature)

                for record in records:
                    if not isinstance(record, dict):
                        continue
                    key = (
                        str(record.get("ticker") or record.get("secCode") or record.get("securityCode") or "").upper(),
                        str(record.get("isin") or "").upper(),
                        str(record.get("classCode") or record.get("class_code") or ""),
                    )
                    if key not in seen_records:
                        seen_records.add(key)
                        all_records.append(record)

                if len(records) < page_size:
                    break
                page += 1

        return all_records

    # ---------------------------------------------------------

    def get_quotes(self, instruments):
        url = f"{self.market_url}/quotes"
        payload = {"instruments": instruments}
        r = RequestHelper.post(
            url,
            headers={**self.headers(), "Content-Type": "application/json"},
            json=payload
        )
        print("Quotes:", r.status_code)
        if r.status_code == 200:
            return r.json()
        return {}

    # ---------------------------------------------------------

    def get_quotes_batch(self, instruments):
        result = []
        batch_size = 100
        for i in range(0, len(instruments), batch_size):
            batch = instruments[i:i + batch_size]
            print("📊 Quotes batch", i // batch_size + 1, len(batch))
            data = self.get_quotes(batch)
            result.extend(data.get("records", []))
        return result

    # ---------------------------------------------------------

    def get_last_trades(self, ticker, class_code):
        url = f"{self.market_url}/last-trades"
        now = datetime.now(timezone.utc)
