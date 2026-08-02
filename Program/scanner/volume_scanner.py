from scanner.instrument_loader import InstrumentLoader
from api.bcs_api import BCSAPI



class VolumeScanner:


    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()



    # ---------------------------------------------------------

    def start(self):

        print(
            "📊 Volume Scanner v0.2"
        )


        instruments = self.loader.load()


        if not instruments:

            print(
                "❌ Нет инструментов"
            )

            return []



        if not self.api.authorize():

            return []



        print(
            "🔎 Отбор ликвидных инструментов..."
        )


        # ---------------------------------
        # готовим запрос котировок
        # ---------------------------------

        quote_list = []


        for item in instruments:


            quote_list.append(

                {

                    "ticker":
                        item["ticker"],

                    "classCode":
                        item["classCode"]

                }

            )



        quotes = self.api.get_quotes_batch(

            quote_list

        )



        liquid = []



        for q in quotes:


            last = q.get(

                "last",

                0

            )


            if last > 0:


                liquid.append(

                    q

                )



        print(

            "Ликвидных инструментов:",

            len(liquid)

        )



        # берём максимум 20

        liquid = liquid[:20]



        result = []



        print(
            "📈 Расчёт объёмов сделок..."
        )



        for q in liquid:


            ticker = q["ticker"]

            class_code = q["classCode"]


            trades = self.api.get_last_trades(

                ticker,

                class_code

            )


            records = trades.get(

                "records",

                []

            )



            money_flow = 0


            quantity_sum = 0



            for trade in records:


                price = trade.get(

                    "price",

                    0

                )


                quantity = trade.get(

                    "quantity",

                    0

                )


                money_flow += (

                    price *

                    quantity

                )


                quantity_sum += quantity



            result.append(

                {

                    "ticker":
                        ticker,

                    "price":
                        q.get(
                            "last",
                            0
                        ),

                    "trades":
                        len(records),

                    "volume":
                        quantity_sum,

                    "money":
                        money_flow

                }

            )


        result.sort(

            key=lambda x:
                x["money"],

            reverse=True

        )


        return result




# ---------------------------------------------------------


if __name__ == "__main__":


    scanner = VolumeScanner()


    data = scanner.start()



    print()

    print(
        "====== VOLUME RANKING ======"
    )



    for row in data:


        print(

            f'{row["ticker"]:8}'
            f' Цена:{row["price"]:10}'
            f' Сделок:{row["trades"]:5}'
            f' Объём:{row["volume"]:8}'
            f' Поток:{row["money"]}'

        )