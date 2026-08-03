"""
Trader_7_12 Pro

Candle Loader Service

Версия 0.1

Назначение:
- получение сделок через TradeService
- передача сделок в CandleService
- подготовка свечей для Momentum Engine
"""


from services.trade_service import TradeService
from services.candle_service import CandleService



class CandleLoaderService:


    def __init__(self):

        self.trade_service = TradeService()

        self.candle_service = CandleService()



    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code,
        timeframe_minutes=5
    ):

        """
        Получение сделок и построение свечей

        ticker:
            SBER

        class_code:
            TQBR / SPBFUT

        timeframe_minutes:
            5
            15
        """



        trades = self.trade_service.load(

            ticker,

            class_code

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