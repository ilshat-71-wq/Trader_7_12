import requests
from datetime import datetime, timedelta

from config import REFRESH_TOKEN
from api.request_helper import RequestHelper


class BCSAPI:

    def __init__(self):

        self.access_token = None

        self.info_url = (
            "https://be.broker.ru/trade-api-information-service/api/v1"
        )

        self.market_url = (
            "https://be.broker.ru/trade-api-market-data-connector/api/v1"
        )

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

        r = RequestHelper.post(
            url,
            data=payload
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

    def get_instruments(
        self,
        instrument_type
    ):

        url = (
            f"{self.info_url}/instruments/by-type"
        )

        params = {
            "type": instrument_type
        }

        r = RequestHelper.get(
            url,
            headers=self.headers(),
            params=params
        )

        print("Instruments:", r.status_code)

        if r.status_code == 200:

            return r.json()

        print(r.text)

        return []

    # ---------------------------------------------------------

    def get_quotes(
        self,
        instruments
    ):

        url = (
            f"{self.market_url}/quotes"
        )

        payload = {
            "instruments": instruments
        }

        r = RequestHelper.post(
            url,
            headers={
                **self.headers(),
                "Content-Type": "application/json"
            },
            json=payload
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

        url = (
            f"{self.market_url}/last-trades"
        )

        end_time = datetime.utcnow()

        start_time = (
            end_time - timedelta(minutes=5)
        )

        payload = {
            "ticker": ticker,
            "classCode": class_code,
            "startDateTime":
                start_time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),
            "endDateTime":
                end_time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),
            "side": side
        }

        if ticker == "AFLT":

            print(
                "\n========== REQUEST AFLT ==========\n"
            )

            print(payload)

            print(
                "\n==================================\n"
            )

        r = RequestHelper.post(
            url,
            headers={
                **self.headers(),
                "Content-Type": "application/json"
            },
            json=payload
        )

        print("Trades:", r.status_code)

        if ticker == "AFLT":

            print(
                "\n========== RESPONSE AFLT ==========\n"
            )

            print(r.json())

            print(
                "\n===================================\n"
            )

        if r.status_code == 200:

            return r.json()

        print(r.text)

        return []