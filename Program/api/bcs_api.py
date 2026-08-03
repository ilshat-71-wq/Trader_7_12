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

from config import REFRESH_TOKEN

from api.request_helper import RequestHelper



class BCSAPI:


    def __init__(self):

        self.access_token = None


        self.info_url = (
            "https://be.broker.ru/"
            "trade-api-information-service/api/v1"
        )


        self.market_url = (
            "https://be.broker.ru/"
            "trade-api-market-data-connector/api/v1"
        )



    # ---------------------------------------------------------

    def authorize(self):

        url = (
            "https://be.broker.ru/"
            "trade-api-keycloak/"
            "realms/tradeapi/"
            "protocol/openid-connect/token"
        )


        payload = {

            "client_id":
                "trade-api-read",

            "grant_type":
                "refresh_token",

            "refresh_token":
                REFRESH_TOKEN

        }



        r = RequestHelper.post(

            url,

            data=payload

        )



        if r.status_code == 200:


            self.access_token = (

                r.json()
                .get(
                    "access_token"
                )

            )


            print(
                "✅ Авторизация БКС успешна"
            )


            return True



        print(
            r.text
        )


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
            instrument_type="FUTURES"
    ):


        url = (

            f"{self.info_url}/"
            "instruments/by-type"

        )


        result = []

        page = 0



        while True:


            params = {

                "type":
                    instrument_type,

                "page":
                    page,

                "size":
                    100

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

                break



            data = r.json()



            if isinstance(
                data,
                list
            ):

                records = data

            else:

                records = data.get(

                    "records",

                    []

                )



            if not records:

                break



            result.extend(

                records

            )



            if len(records) < 100:

                break



            page += 1



        print(

            "Всего загружено:",

            len(result)

        )


        return result



    # ---------------------------------------------------------

    def get_quotes(
            self,
            instruments
    ):


        url = (

            f"{self.market_url}/quotes"

        )



        payload = {

            "instruments":

                instruments

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type":

                    "application/json"

            },

            json=payload

        )



        print(

            "Quotes:",

            r.status_code

        )



        if r.status_code == 200:

            return r.json()



        return {}



    # ---------------------------------------------------------

    def get_quotes_batch(
            self,
            instruments
    ):


        result = []

        batch_size = 100



        for i in range(

            0,

            len(instruments),

            batch_size

        ):


            batch = instruments[

                i:i + batch_size

            ]



            print(

                "📊 Quotes batch",

                i // batch_size + 1,

                len(batch)

            )



            data = self.get_quotes(

                batch

            )



            result.extend(

                data.get(

                    "records",

                    []

                )

            )



        return result



    # ---------------------------------------------------------

    def get_last_trades(
            self,
            ticker,
            class_code
    ):

        url = (
            f"{self.market_url}/last-trades"
        )

        now = datetime.utcnow()

        start = now - timedelta(
            minutes=30
        )

        payload = {

            "ticker": ticker,

            "classCode": class_code,

            "startDateTime": start.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),

            "endDateTime": now.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )

        }


        print("TRADE PAYLOAD:")
        print(payload)


        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type":
                    "application/json"

            },

            json=payload

        )


        print(
            "Trades status:",
            r.status_code
        )


        print(
            "Trades raw:",
            r.text[:500]
        )


        if r.status_code == 200:

            return r.json()


        return {
            "records": []
        }



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


            "ticker":

                ticker,


            "classCode":

                class_code,


            "depth":

                10

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type":

                    "application/json"

            },

            json=payload

        )



        if r.status_code == 200:

            return r.json()



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



        now = datetime.now(

            timezone.utc

        )


        start = now - timedelta(

            hours=4

        )



        payload = {


            "ticker":

                ticker,


            "classCode":

                class_code,


            "interval":

                interval,


            "startDateTime":

                start.strftime(

                    "%Y-%m-%dT%H:%M:%S.000Z"

                ),


            "endDateTime":

                now.strftime(

                    "%Y-%m-%dT%H:%M:%S.000Z"

                )

        }



        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type":

                    "application/json"

            },

            json=payload

        )



        if r.status_code == 200:

            return r.json()



        return {}

    # ---------------------------------------------------------
    # HISTORY TRADES
    # ---------------------------------------------------------

    def get_trades_history(
            self,
            ticker,
            class_code,
            start_time,
            end_time
    ):

        url = (
            f"{self.market_url}/trades"
        )


        payload = {

            "ticker":
                ticker,

            "classCode":
                class_code,

            "startDateTime":
                start_time,

            "endDateTime":
                end_time

        }


        print()

        print(
            "HISTORY TRADES PAYLOAD:"
        )

        print(payload)


        r = RequestHelper.post(

            url,

            headers={

                **self.headers(),

                "Content-Type":
                    "application/json"

            },

            json=payload

        )


        print(
            "History trades status:",
            r.status_code
        )


        print(
            "History trades raw:",
            r.text[:500]
        )


        if r.status_code == 200:

            return r.json()


        return {
            "records": []
        }

