"""
Trader_7_12 Pro

Scanner Engine

Версия 0.3

Назначение:
- загрузка инструментов
- получение котировок
- анализ сделок
- расчет оборота
- рейтинг инструмента
- Volume Price анализ
- построение свечей
- Momentum анализ
- подготовка торгового результата
"""


from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.rating_service import RatingService
from services.candle_service import CandleService
from services.momentum_service import MomentumService

from scanner.signal_engine import SignalEngine

from scanner.volume_price import analyze_volume



class ScannerEngine:


    def __init__(self):

        self.instrument_service = InstrumentService()

        self.quote_service = QuoteService()

        self.trade_service = TradeService()

        self.rating_service = RatingService()

        self.candle_service = CandleService()

        self.momentum_service = MomentumService()

        self.signal_engine = SignalEngine()



    # ---------------------------------------------------------

    def load(self):

        return self.scan()



    # ---------------------------------------------------------

    def scan(self):


        if not self.instrument_service.connect():

            print(
                "❌ Нет соединения BCS"
            )

            return []



        instruments = self.instrument_service.load_stocks()



        print(
            f"Получено инструментов: {len(instruments)}"
        )



        instruments = instruments[:50]



        print(
            f"Сканируем: {len(instruments)}"
        )



        rows = []



        for instrument in instruments:


            ticker = instrument.get(
                "ticker"
            )


            class_code = instrument.get(
                "classCode"
            )


            try:


                print(
                    f"Обработка {ticker}"
                )



                quote = self.quote_service.load(

                    ticker,

                    class_code

                )



                if not isinstance(
                    quote,
                    dict
                ):

                    continue



                last = float(

                    quote.get(
                        "last",
                        0
                    )

                )


                change = float(

                    quote.get(
                        "changeRate",
                        0
                    )

                )



                trades = self.trade_service.load(

                    ticker,

                    class_code

                )



                volume = 0

                money_volume = 0



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



                for trade in records:


                    trade_volume = float(

                        trade.get(
                            "volume",
                            trade.get(
                                "quantity",
                                0
                            )
                        )

                    )


                    price = float(

                        trade.get(
                            "price",
                            0
                        )

                    )



                    volume += trade_volume


                    money_volume += (

                        trade_volume *

                        price

                    )



                # -----------------------------------
                # Rating
                # -----------------------------------

                rating = self.rating_service.calculate(

                    last=last,

                    change=change,

                    volume=volume,

                    money_volume=money_volume

                )



                # -----------------------------------
                # Volume Price
                # -----------------------------------

                volume_analysis = analyze_volume(

                    ticker=ticker,

                    price=last,

                    volume=volume,

                    average_volume=volume

                )



                # -----------------------------------
                # Candle + Momentum
                # -----------------------------------

                momentum = {


                    "momentum_score": 0,

                    "range_position": 0,

                    "signal": ""

                }



                candles = self.candle_service.build_candles(

                    records,

                    timeframe_minutes=5

                )



                if candles:


                    last_candle = candles[-1]


                    momentum = self.momentum_service.analyze(

                        last_candle,

                        average_volume=volume

                    )


                    signal_result = self.signal_engine.analyze(

                        quote,

                        last_candle,

                        volume,

                        money_volume,

                        rating

                    )



                rows.append(

                    ScannerRow(

                        ticker=ticker,

                        last=last,

                        change=change,

                        volume=volume,

                        money_volume=money_volume,

                        rating=rating,


                        volume_ratio=volume_analysis.get(

                            "volume_ratio",

                            0

                        ),


                        volume_score=volume_analysis.get(

                            "volume_score",

                            0

                        ),


                        momentum_score=momentum.get(

                            "momentum_score",

                            0

                        ),


                        range_position=momentum.get(

                            "range_position",

                            0

                        ),


                        signal=momentum.get(

                            "signal",

                            "NO_SIGNAL"

                        ),


                        trade_score=(

                            signal_result.get(
                                "trade_score",
                                0
                            )

                            if signal_result

                            else 0

                        ),


                        confidence=(

                            signal_result.get(
                                "confidence",
                                ""
                            )

                            if signal_result

                            else ""

                        ),


                        direction=(

                            signal_result.get(
                                "direction",
                                ""
                            )

                            if signal_result

                            else ""

                        ),


                        reasons=(

                            signal_result.get(
                                "reasons",
                                []
                            )

                            if signal_result

                            else []

                        )

                    )

                )



            except Exception as e:


                print(

                    "⚠️ Ошибка",

                    ticker,

                    e

                )

                continue



        rows = [

            r for r in rows

            if r.money_volume > 0

        ]


        rows.sort(

            key=lambda x:

            (

                x.trade_score,

                x.momentum_score,

                x.rating,

                x.money_volume

            ),

            reverse=True

        )



        print()

        print(
            "🔥 ТОП сканера:"
        )



        for row in rows[:10]:


            print()

            print(
                row.ticker
            )

            print(
                "Цена:",
                row.last
            )

            print(
                "Оборот:",
                row.money_volume
            )

            print(
                "Rating:",
                row.rating
            )

            print(
                "Trade Score:",
                row.trade_score
            )

            print(
                "Direction:",
                row.direction
            )

            print(
                "Confidence:",
                row.confidence
            )

            print(
                "Reasons:",
                row.reasons
            )

            print(
                "Momentum:",
                row.momentum_score
            )

            print(
                "Range:",
                row.range_position
            )

            print(
                "Signal:",
                row.signal
            )



        return rows