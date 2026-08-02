from models.scanner_row import ScannerRow

from services.instrument_service import InstrumentService
from services.quote_service import QuoteService
from services.trade_service import TradeService
from services.rating_service import RatingService



class ScannerEngine:


    def __init__(self):

        self.instrument_service = InstrumentService()

        self.quote_service = QuoteService()

        self.trade_service = TradeService()

        self.rating_service = RatingService()



    # -------------------------------------------------------------

    # совместимость со старыми тестами

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



        rows = []



        for instrument in instruments:


            ticker = instrument.get(
                "ticker"
            )


            class_code = instrument.get(
                "classCode"
            )



            print(
                f"Обработка {ticker}"
            )



            # -----------------------------
            # QUOTE
            # -----------------------------


            quote = self.quote_service.load(

                ticker,

                class_code

            )



            if not isinstance(quote, dict):

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



            # -----------------------------
            # TRADES
            # -----------------------------


            trades = self.trade_service.load(

                ticker,

                class_code

            )



            volume = 0

            money_volume = 0



            if isinstance(trades, dict):


                records = trades.get(

                    "records",

                    []

                )


            else:

                records = []



            for trade in records:


                quantity = float(

                    trade.get(
                        "quantity",
                        0
                    )

                )


                price = float(

                    trade.get(
                        "price",
                        0
                    )

                )



                volume += quantity


                money_volume += (

                    quantity *

                    price

                )



            # -----------------------------
            # RATING
            # -----------------------------


            rating = self.rating_service.calculate(

                last=last,

                change=change,

                volume=volume,

                money_volume=money_volume

            )



            rows.append(

                ScannerRow(

                    ticker=ticker,

                    last=last,

                    change=change,

                    volume=volume,

                    money_volume=money_volume,

                    rating=rating

                )

            )



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


            print(

                row.ticker,

                "Цена:",
                row.last,

                "Объём:",
                row.volume,

                "Оборот:",
                row.money_volume,

                "Rating:",
                row.rating

            )



        return rows