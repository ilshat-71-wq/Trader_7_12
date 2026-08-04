"""
Trader_7_12 Pro

Scanner Engine

Версия 0.2

Назначение:
- загрузка инструментов
- получение котировок
- анализ сделок
- расчет оборота
- рейтинг инструмента
- Volume Price анализ
- подготовка торгового результата
"""


from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.rating_service import RatingService

from scanner.volume_price import analyze_volume



class ScannerEngine:


    def __init__(self):

        self.instrument_service = InstrumentService()

        self.quote_service = QuoteService()

        self.trade_service = TradeService()

        self.rating_service = RatingService()



    # -------------------------------------------------------------

    def load(self):

        return self.scan()



    # -------------------------------------------------------------

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
                            0
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
                # Rating Engine
                # -----------------------------------

                rating = self.rating_service.calculate(

                    last=last,

                    change=change,

                    volume=volume,

                    money_volume=money_volume

                )



                # -----------------------------------
                # Volume Price Analyzer
                # -----------------------------------

                volume_analysis = analyze_volume(

                    ticker=ticker,

                    price=last,

                    volume=volume,

                    average_volume=volume

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

                        momentum_score=volume_analysis.get(

                            "momentum_score",

                            0

                        ),

                        range_position=volume_analysis.get(

                            "range_position",

                            0

                        ),

                        signal=volume_analysis.get(

                            "signal",

                            ""

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



        rows.sort(

            key=lambda x:

            (

                x.rating,

                x.money_volume,

                abs(x.change)

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
                "Volume:",
                row.volume_ratio
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