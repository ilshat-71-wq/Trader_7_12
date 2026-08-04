"""
Trader_7_12 Pro

Live Trade Collector

Версия 0.2

Назначение:
- получение сделок BCS
- работа с периодом времени
- подготовка потока сделок для анализа
"""


from datetime import datetime, timedelta, timezone

from api.bcs_api import BCSAPI



class LiveTradeCollector:


    def __init__(self):

        self.api = BCSAPI()

        self.api.authorize()



    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code,
        start_time=None,
        end_time=None
    ):


        print()

        print(
            f"LiveTradeCollector: {ticker} {class_code}"
        )


        if end_time is None:

            end_time = datetime.now(
                timezone.utc
            )


        if start_time is None:

            start_time = end_time - timedelta(
                minutes=30
            )


        result = self.api.get_last_trades(

            ticker,

            class_code

        )


        if isinstance(
            result,
            dict
        ):

            return result.get(

                "records",

                []

            )


        return []
