"""
Trader_7_12 Pro

Volume Scanner

Версия 0.3

Назначение:
- расчёт ликвидности инструментов
- денежный оборот
- рейтинг активности
"""


from scanner.instrument_loader import InstrumentLoader
from api.bcs_api import BCSAPI



class VolumeScanner:


    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()



    # ---------------------------------------------------------

    def start(self):

        print(
            "📊 Volume Scanner v0.3"
        )


        instruments = self.loader.load()


        if not instruments:

            print(
                "❌ Нет инструментов"
            )

            return []



        if not self.api.authorize():

            print(
                "❌ Ошибка авторизации"
            )

            return []



        result = []



        for item in instruments[:50]:


            ticker = item.get(
                "ticker"
            )


            class_code = item.get(
                "classCode"
            )



            trades = self.api.get_last_trades(

                ticker,

                class_code

            )



            records = trades.get(
                "records",
                []
            )



            trade_count = len(records)



            money_volume = 0



            total_quantity = 0



            for trade in records:


                price = (

                    trade.get("price")

                    or

                    trade.get("last")

                    or

                    trade.get("tradePrice")

                    or

                    0

                )


                quantity = (

                    trade.get("quantity")

                    or

                    trade.get("volume")

                    or

                    trade.get("amount")

                    or

                    0

                )


                try:

                    money_volume += (

                        float(price)

                        *

                        float(quantity)

                    )


                    total_quantity += float(quantity)


                except:

                    pass



            average_trade = 0


            if trade_count:

                average_trade = (

                    money_volume /

                    trade_count

                )



            result.append(

                {

                    "ticker":

                        ticker,


                    "trades":

                        trade_count,


                    "money_volume":

                        money_volume,


                    "quantity":

                        total_quantity,


                    "average_trade":

                        average_trade

                }

            )



        result.sort(

            key=lambda x:

            x["money_volume"],

            reverse=True

        )



        print()

        print(
            "🔥 TOP LIQUIDITY"
        )


        for row in result[:10]:

            print(

                row["ticker"],

                "Сделок:",

                row["trades"],

                "Оборот:",

                row["money_volume"]

            )



        return result





# ---------------------------------------------------------


if __name__ == "__main__":


    scanner = VolumeScanner()


    data = scanner.start()


    print()

    print(
        "Готово:",
        len(data)
    )