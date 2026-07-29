from scanner.instrument_loader import InstrumentLoader
from api.bcs_api import BCSAPI


class MarketScanner:

    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()



    # ---------------------------------------------------------

    def start(self):

        print("🚀 Market Scanner v0.3")


        instruments = self.loader.load()


        if not instruments:

            print(
                "❌ Инструменты не найдены"
            )

            return []



        print()

        print(
            "Активных контрактов:",
            len(instruments)
        )


        if not self.api.authorize():

            return []



        quotes_request = []


        for item in instruments:


            quotes_request.append(

                {

                    "ticker":
                        item["ticker"],

                    "classCode":
                        item["classCode"]

                }

            )



        quotes = self.api.get_quotes(
            quotes_request
        )



        records = quotes.get(
            "records",
            []
        )



        result = []



        for item in records:


            bid = item.get(
                "bid",
                0
            )


            offer = item.get(
                "offer",
                0
            )


            last = item.get(
                "last",
                0
            )


            change = item.get(
                "changeRate",
                0
            )



            spread = 0


            if bid and offer:

                spread = round(

                    offer - bid,

                    4

                )



            power = abs(change)



            if spread > 0:

                power = power / spread



            result.append(

                {

                    "ticker":
                        item.get(
                            "ticker"
                        ),

                    "price":
                        last,

                    "change":
                        change,

                    "spread":
                        spread,

                    "power":
                        round(
                            power,
                            2
                        )

                }

            )



        result.sort(

            key=lambda x:
                x["power"],

            reverse=True

        )


        return result




# ---------------------------------------------------------


if __name__ == "__main__":


    scanner = MarketScanner()


    data = scanner.start()



    print()

    print(
        "====== MARKET SCANNER RESULT ======"
    )



    for row in data:


        print(

            f'{row["ticker"]:8}'
            f' Цена: {row["price"]:10}'
            f' Изм: {row["change"]:7}%'
            f' Спред: {row["spread"]:8}'
            f' Сила: {row["power"]}'

        )