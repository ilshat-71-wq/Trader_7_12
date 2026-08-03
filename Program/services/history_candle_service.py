"""
Trader_7_12 Pro

History Candle Service

Версия 0.1

Назначение:
- загрузка исторических сделок
- построение свечей
- подготовка данных для анализа
"""


from services.trade_service import TradeService
from services.candle_service import CandleService



class HistoryCandleService:


    def __init__(self):

        self.trade_service = TradeService()

        self.candle_service = CandleService()



    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code,
        start_time,
        end_time,
        timeframe_minutes=5
    ):


        trades = self.trade_service.load_history(

            ticker,

            class_code,

            start_time,

            end_time

        )


        if not trades:

            return []



        if isinstance(
            trades,
            dict
        ):

            records = trades.get(

                "records",

                []

            )

        else:

            records = []



        if not records:

            return []



        candles = self.candle_service.build_candles(

            records,

            timeframe_minutes

        )


        return candles