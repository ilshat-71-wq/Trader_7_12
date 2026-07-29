"""
Trader_7_12 Pro

Market Loader

Версия 0.5

Назначение:
- подключение к BCS API
- загрузка рыночных данных
"""


import requests

from config import REFRESH_TOKEN





class BCSAPI:


    def __init__(self):

        self.access_token = None

        self.base_url = (
            "https://be.broker.ru/"
            "trade-api-information-service/api/v1"
        )



    def authorize(self):

        url = (
            "https://be.broker.ru/"
            "trade-api-keycloak/"
            "realms/tradeapi/"
            "protocol/openid-connect/token"
        )


        payload = {

            "client_id": "trade-api-read",

            "grant_type": "refresh_token",

            "refresh_token": REFRESH_TOKEN

        }


        response = requests.post(

            url,

            data=payload

        )


        if response.status_code == 200:

            self.access_token = (
                response.json()["access_token"]
            )

            print(
                "✅ Авторизация БКС успешна"
            )

            return True


        print(response.text)

        return False




    def headers(self):

        return {

            "Authorization":
            f"Bearer {self.access_token}"

        }




    def get_instruments(
            self,
            instrument_type="FUTURES"
    ):


        url = (
            f"{self.base_url}/"
            "instruments/by-type"
        )


        params = {

            "type": instrument_type

        }


        response = requests.get(

            url,

            headers=self.headers(),

            params=params

        )


        print(
            "BCS response:",
            response.status_code
        )


        if response.status_code == 200:

            return response.json()


        print(response.text)

        return None






class MarketLoader:


    def __init__(self):

        self.api = BCSAPI()

        self.data = None



    def connect(self):

        return self.api.authorize()



    def load(self):

        """
        Метод вызывается из main.py

        Загружает фьючерсы
        """

        print(
            "📊 Загрузка инструментов рынка..."
        )


        if self.api.access_token is None:

            if not self.connect():

                return None



        self.data = self.api.get_instruments(

            "FUTURES"

        )


        if self.data:

            print(
                "✅ Инструменты загружены:",
                len(self.data)
                if isinstance(self.data, list)
                else "OK"
            )


        else:

            print(
                "⚠️ Данные рынка не получены"
            )


        return self.data




    def load_instruments(
            self,
            instrument_type="FUTURES"
    ):

        return self.api.get_instruments(

            instrument_type

        )