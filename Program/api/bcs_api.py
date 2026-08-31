"""
Trader_7_12 Pro

BCS API

Версия 0.9

Назначение:
- авторизация BCS
- инструменты
- котировки
- сделки
- стакан
- свечи
"""

from datetime import datetime, timedelta, timezone
import threading

from config import get_refresh_token, save_refresh_token
from api.request_helper import RequestHelper


class BCSAPI:

    CANDLE_CACHE_TTL = 30.0
    CANDLE_TIMEOUT = 3.0
    CANDLE_RETRIES = 2
    CANDLE_MAX_CONCURRENCY = 1
    METADATA_TIMEOUT = 5.0
    METADATA_RETRIES = 2

    _shared_instance = None
    _initialized = False

    def __new__(cls):
        """Return one process-wide read-only market-data client.

        Scanner services are composed from several layers, and historically
        each layer created its own BCSAPI. That caused repeated authorization,
        independent candle caches and unnecessary concurrent HTTP load.
        Keep one client instance while preserving the existing BCSAPI API.
        """
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
        # Reuse an already authorized shared client. This prevents every
        # nested service from refreshing the same BCS access token again.
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
            # Keycloak/BCS may rotate the refresh token. Persist the newest
            # value locally so the next process/session continues seamlessly.
            rotated_token = data.get("refresh_token")
            if rotated_token:
                save_refresh_token(rotated_token)
            elif not __import__("os").getenv("BCS_REFRESH_TOKEN"):
                # The token was already loaded from the local secure file.
                # Keep that file as the source of truth.
                pass
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
        if not isinstance(tickers, (list, tuple)):
            return []
        requested = [str(t).strip().upper() for t in tickers if str(t).strip()]
        if not requested:
            return []
        url = f"{self.info_url}/instruments/by-tickers"
        payload = {"tickers": requested}
        try:
            r = RequestHelper.post(
                url,
                headers={**self.headers(), "Content-Type": "application/json"},
                json=payload
            )
        except Exception as exc:
            print("Instrument ticker lookup failed:", type(exc).__name__)
            return []
        print("Instrument ticker lookup:", r.status_code)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except ValueError:
            return []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("instruments", data.get("records", []))
        else:
            records = []
        return records if isinstance(records, list) else []

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
        start_time = now - timedelta(minutes=30)
        payload = {
            "ticker": ticker,
            "classCode": class_code,
            "startDateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDateTime": now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        try:
            r = RequestHelper.post(
                url,
                headers={**self.headers(), "Content-Type": "application/json"},
                json=payload
            )
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

    # ---------------------------------------------------------

    def get_order_book(self, ticker, class_code):
        """Load the current Level-2 book through BCS's documented GET endpoint."""
        url = f"{self.market_url}/order-book"
        params = {"ticker": ticker, "classCode": class_code, "depth": 10}
        try:
            r = RequestHelper.get(
                url,
                headers=self.headers(),
                params=params,
                timeout=self.METADATA_TIMEOUT,
                max_retries=self.METADATA_RETRIES,
            )
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

    # ---------------------------------------------------------

    @staticmethod
    def _candle_cache_key(ticker, class_code, interval, start_dt, end_dt):
        """Use minute precision so equivalent scan requests share one cache entry."""
        start_key = start_dt.replace(second=0, microsecond=0).isoformat()
        end_key = end_dt.replace(second=0, microsecond=0).isoformat()
        return (str(ticker).upper(), str(class_code), str(interval).upper(), start_key, end_key)

    def get_candles(self, ticker, class_code, interval="M5", start_time=None, end_time=None):
        """Load BCS candles with bounded retry, cache and concurrency control.

        All candles-chart HTTP calls pass through one semaphore on the shared
        BCSAPI instance. This limits candle endpoint concurrency without
        serializing the rest of the scanner.
        """
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

        params = {
            "ticker": ticker,
            "classCode": class_code,
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "timeFrame": interval
        }

        try:
            with self._candle_semaphore:
                r = RequestHelper.get(
                    url,
                    headers=self.headers(),
                    params=params,
                    timeout=self.CANDLE_TIMEOUT,
                    max_retries=self.CANDLE_RETRIES,
                )
        except Exception as exc:
            print("⚠️ Candle request failed:", ticker, interval, type(exc).__name__)
            return {}

        if r.status_code != 200:
            return {}

        try:
            data = r.json()
        except ValueError:
            print("❌ Candles JSON error")
            return {}

        self._candle_cache[cache_key] = (now, data)
        return data

    # ---------------------------------------------------------
    # HISTORY TRADES
    # ---------------------------------------------------------

    def get_trades_period(self, ticker, class_code, start_time, end_time):
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        records = []
        current = start
        while current < end:
            chunk_end = min(current + timedelta(hours=1), end)
            payload = {
                "ticker": ticker,
                "classCode": class_code,
                "startDateTime": current.isoformat(),
                "endDateTime": chunk_end.isoformat()
            }
            print("\nPERIOD TRADES PAYLOAD:")
            print(payload)
            r = RequestHelper.post(
                f"{self.market_url}/last-trades",
                headers={**self.headers(), "Content-Type": "application/json"},
                json=payload
            )
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
