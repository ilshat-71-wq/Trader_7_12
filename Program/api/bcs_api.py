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

    def get_instruments_by_tickers(self, tickers):
        """Resolve exact instrument metadata by ticker via BCS."""
        if not isinstance(tickers, (list, tuple)):
            return []

        requested = [
            str(ticker).strip().upper()
            for ticker in tickers
            if str(ticker).strip()
        ]
        if not requested:
            return []

        url = f"{self.info_url}/instruments/by-tickers"
        payload = {"tickers": requested}

        try:
            r = RequestHelper.post(
                url,
                headers={
                    **self.headers(),
                    "Content-Type": "application/json"
                },
                json=payload
            )
        except Exception as exc:
            print(
                "Instrument ticker lookup failed:",
                type(exc).__name__
            )
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
        """Load recent futures trades for confirmation."""

        url = f"{self.market_url}/last-trades"

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=30)

        payload = {
            "ticker": ticker,
            "classCode": class_code,
            "startDateTime": start_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            "endDateTime": now.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        }

        try:
            r = RequestHelper.post(
                url,
                headers={
                    **self.headers(),
                    "Content-Type": "application/json"
                },
                json=payload
            )
        except Exception as exc:
            print(
                "⚠️ Trades request failed:",
                ticker,
                class_code,
                type(exc).__name__,
                str(exc)
            )
            return {"records": []}

        if r.status_code != 200:
            print(
                "⚠️ Trades HTTP:",
                ticker,
                class_code,
                r.status_code,
                r.text[:300]
            )
            return {"records": []}

        try:
            data = r.json()
        except ValueError:
            print(
                "⚠️ Trades JSON parse failed:",
                ticker,
                class_code
            )
            return {"records": []}

        records = data.get("records", [])

        if not isinstance(records, list):
            records = []

        records.sort(
            key=lambda x: x.get(
                "dateTime",
                x.get("time", "")
            )
        )

        print(
            "TRADES COLLECTED:",
            ticker,
            class_code,
            len(records)
        )

        if records:
            print(
                "FIRST TRADE:",
                records[0].get(
                    "dateTime",
                    records[0].get("time")
                ),
                records[0].get("price")
            )
            print(
                "LAST TRADE:",
                records[-1].get(
                    "dateTime",
                    records[-1].get("time")
                ),
                records[-1].get("price")
            )

        return {"records": records}


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
        interval="M5",
        start_time=None,
        end_time=None
    ):
        """
        Загрузка исторических свечей BCS.

        Поддерживаемые BCS timeFrame:

            M1
            M5
            M15
            M30
            H1
            H4
            D

        Для дневных свечей используется:
            D

        D1 / DAY / 1D не используются.

        Если start_time/end_time не переданы,
        используется стандартное окно последних 4 часов.
        """

        url = (
            f"{self.market_url}/candles-chart"
        )

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
            if end_time is not None:
                end_dt = normalize_time(end_time)
            else:
                end_dt = now
            if start_time is not None:
                start_dt = normalize_time(start_time)
            else:
                if interval == "D":
                    start_dt = end_dt - timedelta(days=30)
                else:
                    start_dt = end_dt - timedelta(hours=4)
        except (TypeError, ValueError) as exc:
            print()
            print("❌ Invalid candle time:", exc)
            return {}

        if start_dt is None or end_dt is None:
            return {}
        if start_dt >= end_dt:
            print()
            print("❌ Invalid candle period")
            print("START:", start_dt)
            print("END:", end_dt)
            return {}

        params = {
            "ticker": ticker,
            "classCode": class_code,
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "timeFrame": interval
        }

        r = RequestHelper.get(
            url,
            headers=self.headers(),
            params=params
        )

        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                print("❌ Candles JSON error")
                return {}
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



    # ---------------------------------------------------------

    def get_trades_period(
            self,
            ticker,
            class_code,
            start_time,
            end_time
    ):

        from datetime import datetime, timedelta

        start = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )

        end = datetime.fromisoformat(
            end_time.replace("Z", "+00:00")
        )

        records = []

        current = start

        while current < end:

            chunk_end = min(
                current + timedelta(hours=1),
                end
            )

            payload = {
                "ticker": ticker,
                "classCode": class_code,
                "startDateTime": current.isoformat(),
                "endDateTime": chunk_end.isoformat()
            }

            print()
            print("PERIOD TRADES PAYLOAD:")
            print(payload)

            r = RequestHelper.post(
                f"{self.market_url}/last-trades",
                headers={
                    **self.headers(),
                    "Content-Type": "application/json"
                },
                json=payload
            )

            print(
                "Period trades status:",
                r.status_code
            )

            if r.status_code == 200:

                data = r.json()

                chunk_records = data.get(
                    "records",
                    []
                )

                records.extend(
                    chunk_records
                )

                print(
                    "Chunk records:",
                    len(chunk_records)
                )

            else:

                print(
                    "Period trades raw:",
                    r.text[:500]
                )

            current = chunk_end

        return {
            "records": records
        }
