from scanner.instrument_loader import InstrumentLoader
from api.bcs_api import BCSAPI


class VolumeScanner:

    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()



    # ---------------------------------------------------------

    def start(self):

        print("📊 Volume Scanner v0.1")


        instruments = self.loader.load()


        if not instruments:

            print("❌ Нет инструментов")

            return []



        if not self.api.authorize():

            return []



        result = []



        for item in instruments:


            ticker = item["ticker"]

            class_code = item["classCode"]



            trades = self.api.get_last_trades(

                ticker,

                class_code

            )


            records = trades.get(

                "records",

                []

            )


            trade_count = len(records)



            money_flow = 0



            for trade in records:


                price = trade.get(

                    "price",

                    0

                )


                volume = trade.get(

                    "quantity",

                    0

                )


                money_flow += (

                    price *

                    volume

                )



            result.append(

                {

                    "ticker":
                        ticker,

                    "trades":
                        trade_count,

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
            f' Сделок: {row["trades"]:5}'
            f' Поток: {row["money"]}'

        )