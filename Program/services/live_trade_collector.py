"""
Trader_7_12 Pro

Live Trade Collector

Версия 0.2

Назначение:
- получение сделок BCS
- работа с произвольным периодом
- подготовка потока сделок для анализа
"""


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
        start_time,
        end_time
    ):


        print()

        print(
            f"LiveTradeCollector: {ticker} {class_code}"
        )


        result = self.api.get_trades_period(

            ticker,

            class_code,

            start_time,

            end_time

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
