import time
import requests


class RequestHelper:
    """Small HTTP helper with a fail-fast profile for scanner reads."""

    # A failed market-data request must not stall the whole scanner for minutes.
    # Callers that need a more tolerant request can override these per call.
    MAX_RETRIES = 1
    RETRY_DELAY = 0.2
    REQUEST_TIMEOUT = 8

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

    # ---------------------------------------------------------

    @staticmethod
    def post(
        url,
        headers=None,
        json=None,
        data=None,
        timeout=None,
        max_retries=None,
    ):
        retries = (
            RequestHelper.MAX_RETRIES
            if max_retries is None
            else max(1, int(max_retries))
        )
        request_timeout = (
            RequestHelper.REQUEST_TIMEOUT
            if timeout is None
            else max(0.1, float(timeout))
        )

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=json,
                    data=data,
                    timeout=request_timeout
                )

                if response.status_code in RequestHelper.RETRY_HTTP_CODES:
                    print(
                        f"Retry {attempt}/{retries}: HTTP {response.status_code}"
                    )
                    if attempt < retries:
                        time.sleep(RequestHelper.RETRY_DELAY)
                        continue

                return response

            except RequestHelper.REQUEST_EXCEPTIONS as error:
                print(
                    f"Retry {attempt}/{retries}: {type(error).__name__}"
                )
                if attempt < retries:
                    time.sleep(RequestHelper.RETRY_DELAY)

        raise RuntimeError(
            f"Не удалось выполнить POST после {retries} попытки(ок)."
        )

    # ---------------------------------------------------------

    @staticmethod
    def get(
        url,
        headers=None,
        params=None,
        timeout=None,
        max_retries=None,
    ):
        retries = (
            RequestHelper.MAX_RETRIES
            if max_retries is None
            else max(1, int(max_retries))
        )
        request_timeout = (
            RequestHelper.REQUEST_TIMEOUT
            if timeout is None
            else max(0.1, float(timeout))
        )

        for attempt in range(1, retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=request_timeout
                )

                if response.status_code in RequestHelper.RETRY_HTTP_CODES:
                    print(
                        f"Retry {attempt}/{retries}: HTTP {response.status_code}"
                    )
                    if attempt < retries:
                        time.sleep(RequestHelper.RETRY_DELAY)
                        continue

                return response

            except RequestHelper.REQUEST_EXCEPTIONS as error:
                print(
                    f"Retry {attempt}/{retries}: {type(error).__name__}"
                )
                if attempt < retries:
                    time.sleep(RequestHelper.RETRY_DELAY)

        raise RuntimeError(
            f"Не удалось выполнить GET после {retries} попытки(ок)."
        )
