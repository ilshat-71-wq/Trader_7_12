import requests
from datetime import datetime, timedelta

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import REFRESH_TOKEN


class BCSAPI:

    def __init__(self):

        self.access_token = None

        self.info_url = (
            "https://be.broker.ru/trade-api-information-service/api/v1"
        )

        self.market_url = (
            "https://be.broker.ru/trade-api-market-data-connector/api/v1"
        )

        # ---------- Session ----------

        self.session = requests.Session()

        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=0.4,
            status_forcelist=[
                429,
                500,
                502,
                503,
                504
            ],
            allowed_methods=[
                "GET",
                "POST"
            ]
        )

        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=20,
            pool_maxsize=20
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    # ---------------------------------------------------------

    def authorize(self):

        url = (
            "https://be.broker.ru/"
            "trade-api-keycloak/realms/tradeapi/"
            "protocol/openid-connect/token"
        )

        payload = {
            "client_id": "trade-api-read",
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        }

        r = self.session.post(
            url,
            data=payload,
            timeout=20
        )

        if r.status_code == 200:

            self.access_token = r.json()["access_token"]

            print("✅ Авторизация БКС успешна")

            return True

        print(r.text)

        return False

    # ---------------------------------------------------------

    def headers(self):

        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    # ---------------------------------------------------------

    def get_instruments(self, instrument_type):

        url = f"{self.info_url}/instruments/by-type"

        params = {
            "type": instrument_type
        }

        r = self.session.get(
            url,
            headers=self.headers(),
            params=params,
            timeout=20
        )

        print("Instruments:", r.status_code)

        if r.status_code == 200:
            return r.json()

        print(r.text)

        return []

    # ---------------------------------------------------------

    def get_quotes(self, instruments):

        url = f"{self.market_url}/quotes"

        payload = {
            "instruments": instruments
        }

        r = self.session.post(
            url,
            headers={
                **self.headers(),
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        print("Quotes:", r.status_code)

        if r.status_code == 200:
            return r.json()

        print(r.text)

        return []

    # ---------------------------------------------------------

    def get_last_trades(
        self,
        ticker,
        class_code,
        side="1"
    ):

        url = f"{self.market_url}/last-trades"

        end_time = datetime.utcnow()

        start_time = end_time - timedelta(minutes=5)

        payload = {
            "ticker": ticker,
            "classCode": class_code,
            "startDateTime": start_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "endDateTime": end_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "side": side
        }

        r = self.session.post(
            url,
            headers={
                **self.headers(),
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        print("Trades:", r.status_code)

        if r.status_code == 200:
            return r.json()

        print(r.text)

        return []