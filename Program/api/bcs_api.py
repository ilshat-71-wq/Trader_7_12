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
            "refresh_token": REFRESH_TOKEN
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
            "Authorization":
                f"Bearer {self.access_token}"
        }



    # ---------------------------------------------------------

    def get_instruments(
        self,
        instrument_type
    ):


        url = (
            f"{self.info_url}/instruments/by-type"
        )


        all_records = []

        page = 0



        while True:

            params = {

                "type": instrument_type,

                "page": page,

                "size": 100

            }


            r = RequestHelper.get(

                url,

                headers=self.headers(),

                params=params

            )


            print(
                f"Instruments page {page}:",
                r.status_code
            )


            if r.status_code != 200:

                print(r.text)

                break



            data = r.json()



            if isinstance(data, list):

                records = data

            else:

                records = data.get(
                    "records",
                    []
                )



            if not records:

                break



            all_records.extend(
                records
            )


            if len(records) < 100:

                break



            page += 1



        print(
            "Всего загружено:",
            len(all_records)
        )


        return all_records



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



        print(
            "Quotes:",
            r.status_code
        )



        if r.status_code == 200:

            data = r.json()

            print(
                "\n========== RAW QUOTES ==========\n"
            )

            print(data)

            print(
                "\n===============================\n"
            )

            return data



        print(r.text)

        return {}



    # ---------------------------------------------------------

    def get_last_trades(
        self,
        ticker,
        class_code
    ):


        url = (
            f"{self.market_url}/last-trades"
        )


        end_time = datetime.utcnow()


        start_time = (
            end_time - timedelta(minutes=15)
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
                )

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type": "application/json"

            },

            json=payload

        )


        print(
            f"Trades {ticker}:",
            r.status_code
        )


        if r.status_code == 200:

            return r.json()



        print(r.text)

        return {}



    # ---------------------------------------------------------

    def get_order_book(
        self,
        ticker,
        class_code
    ):


        url = (
            f"{self.market_url}/order-book"
        )


        payload = {

            "ticker": ticker,

            "classCode": class_code,

            "depth": 10

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type": "application/json"

            },

            json=payload

        )



        print(
            f"OrderBook {ticker}:",
            r.status_code
        )


        if r.status_code == 200:

            return r.json()



        print(r.text)

        return {}



    # ---------------------------------------------------------

    def get_candles(
        self,
        ticker,
        class_code,
        interval="MINUTE_5"
    ):


        url = (
            f"{self.market_url}/candles"
        )


        end_time = datetime.utcnow()


        start_time = (
            end_time - timedelta(hours=4)
        )


        payload = {

            "ticker": ticker,

            "classCode": class_code,

            "interval": interval,

            "startDateTime":
                start_time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                ),

            "endDateTime":
                end_time.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z"
                )

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type": "application/json"

            },

            json=payload

        )


        print(
            f"Candles {ticker}:",
            r.status_code
        )



        if r.status_code == 200:

            data = r.json()


            print(
                "\n========== RAW CANDLES",
                ticker,
                "=========="
            )

            print(data)

            print(
                "====================================\n"
            )


            return data



        print(r.text)

        return {}