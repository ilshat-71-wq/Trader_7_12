import requests

from config import REFRESH_TOKEN


class BCSAPI:

    def __init__(self):
        self.access_token = None
        self.base_url = "https://be.broker.ru/trade-api-information-service/api/v1"

    def authorize(self):

        url = "https://be.broker.ru/trade-api-keycloak/realms/tradeapi/protocol/openid-connect/token"

        payload = {
            "client_id": "trade-api-read",
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        }

        r = requests.post(url, data=payload)

        if r.status_code == 200:
            self.access_token = r.json()["access_token"]
            print("✅ Авторизация БКС успешна")
            return True

        print(r.text)
        return False

    def headers(self):

        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_instruments(self, instrument_type):

        url = f"{self.base_url}/instruments/by-type"

        params = {
            "type": instrument_type
        }

        r = requests.get(
            url,
            headers=self.headers(),
            params=params
        )

        print(r.status_code)

        if r.status_code == 200:
            return r.json()

        print(r.text)
        return None

    def get_quotes(self, instruments):

        url = "https://be.broker.ru/trade-api-market-data-connector/api/v1/quotes"

        payload = {
            "instruments": instruments
        }

        r = requests.post(
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
        return None