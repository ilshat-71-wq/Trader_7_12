import time
import threading
import requests


class RequestHelper:
    """Small HTTP helper with bounded retry and global request-start throttling."""

    MAX_RETRIES = 1
    RETRY_DELAY = 0.2
    REQUEST_TIMEOUT = 8

    # BCS documents a 10 RPS market-data limit. Keep request starts below it
    # across scanner worker threads and across GET/POST calls.
    REQUEST_INTERVAL = 0.15
    _rate_lock = threading.Lock()
    _last_request_at = 0.0

    RETRY_HTTP_CODES = {
        429,
        500,
        502,
        503,
        504
    }

    REQUEST_EXCEPTIONS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ReadTimeout,
        requests.exceptions.SSLError,
        requests.exceptions.ChunkedEncodingError,
    )

    @classmethod
    def _wait_for_request_slot(cls):
        """Rate-limit request starts without serializing response handling."""
        with cls._rate_lock:
            now = time.monotonic()
            wait = cls.REQUEST_INTERVAL - (now - cls._last_request_at)
            if wait > 0:
                time.sleep(wait)
            cls._last_request_at = time.monotonic()

    @classmethod
    def _get_with_limit(cls, url, headers=None, params=None, timeout=None):
        cls._wait_for_request_slot()
        return requests.get(url, headers=headers, params=params, timeout=timeout)

    @classmethod
    def _post_with_limit(cls, url, headers=None, json=None, data=None, timeout=None):
        cls._wait_for_request_slot()
        return requests.post(url, headers=headers, json=json, data=data, timeout=timeout)

    @classmethod
    def post(cls, url, headers=None, json=None, data=None, timeout=None, max_retries=None):
        retries = cls.MAX_RETRIES if max_retries is None else max(1, int(max_retries))
        request_timeout = cls.REQUEST_TIMEOUT if timeout is None else max(0.1, float(timeout))

        for attempt in range(1, retries + 1):
            try:
                response = cls._post_with_limit(url, headers=headers, json=json, data=data, timeout=request_timeout)
                if response.status_code in cls.RETRY_HTTP_CODES:
                    print(f"Retry {attempt}/{retries}: HTTP {response.status_code}")
                    if attempt < retries:
                        time.sleep(cls.RETRY_DELAY)
                        continue
                return response
            except cls.REQUEST_EXCEPTIONS as error:
                print(f"Retry {attempt}/{retries}: {type(error).__name__}")
                if attempt < retries:
                    time.sleep(cls.RETRY_DELAY)

        raise RuntimeError(f"Не удалось выполнить POST после {retries} попытки(ок).")

    @classmethod
    def get(cls, url, headers=None, params=None, timeout=None, max_retries=None):
        retries = cls.MAX_RETRIES if max_retries is None else max(1, int(max_retries))
        request_timeout = cls.REQUEST_TIMEOUT if timeout is None else max(0.1, float(timeout))

        for attempt in range(1, retries + 1):
            try:
                response = cls._get_with_limit(url, headers=headers, params=params, timeout=request_timeout)
                if response.status_code in cls.RETRY_HTTP_CODES:
                    print(f"Retry {attempt}/{retries}: HTTP {response.status_code}")
                    if attempt < retries:
                        time.sleep(cls.RETRY_DELAY)
                        continue
                return response
            except cls.REQUEST_EXCEPTIONS as error:
                print(f"Retry {attempt}/{retries}: {type(error).__name__}")
                if attempt < retries:
                    time.sleep(cls.RETRY_DELAY)

        raise RuntimeError(f"Не удалось выполнить GET после {retries} попытки(ок).")
