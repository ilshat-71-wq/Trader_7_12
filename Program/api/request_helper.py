import time
import requests


class RequestHelper:

    MAX_RETRIES = 3

    RETRY_DELAY = 0.5

    RETRY_HTTP_CODES = {
        429,
        500,
        502,
        503,
        504
    }

    # ---------------------------------------------------------

    @staticmethod
    def post(
        url,
        headers=None,
        json=None,
        data=None
    ):

        for attempt in range(1, RequestHelper.MAX_RETRIES + 1):

            try:

                response = requests.post(
                    url,
                    headers=headers,
                    json=json,
                    data=data,
                    timeout=15
                )

                #
                # Если сервер просит повторить
                #
                if response.status_code in RequestHelper.RETRY_HTTP_CODES:

                    print(
                        f"Retry {attempt}: HTTP {response.status_code}"
                    )

                    time.sleep(RequestHelper.RETRY_DELAY)

                    continue

                return response

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.SSLError,
                requests.exceptions.ChunkedEncodingError
            ) as error:

                print(
                    f"Retry {attempt}: {type(error).__name__}"
                )

                time.sleep(RequestHelper.RETRY_DELAY)

        raise RuntimeError(
            "Не удалось выполнить POST после повторных попыток."
        )

    # ---------------------------------------------------------

    @staticmethod
    def get(
        url,
        headers=None,
        params=None
    ):

        for attempt in range(1, RequestHelper.MAX_RETRIES + 1):

            try:

                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=15
                )

                if response.status_code in RequestHelper.RETRY_HTTP_CODES:

                    print(
                        f"Retry {attempt}: HTTP {response.status_code}"
                    )

                    time.sleep(RequestHelper.RETRY_DELAY)

                    continue

                return response

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.SSLError,
                requests.exceptions.ChunkedEncodingError
            ) as error:

                print(
                    f"Retry {attempt}: {type(error).__name__}"
                )

                time.sleep(RequestHelper.RETRY_DELAY)

        raise RuntimeError(
            "Не удалось выполнить GET после повторных попыток."
        )