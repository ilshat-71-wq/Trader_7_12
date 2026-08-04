"""
Trader_7_12 Pro

Volume Scanner

Версия 0.4

Назначение:
- расчёт ликвидности инструментов
- денежный оборот
- сила объёма
- импульс цены
- подготовка данных для Signal Engine
"""


from scanner.instrument_loader import InstrumentLoader
from scanner.volume_price import analyze_volume
from api.bcs_api import BCSAPI



class VolumeScanner:


    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()



    def start(self):

        print(
            "📊 Volume Scanner v0.4"
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



            if not records:

                continue



            total_volume = 0

            money_volume = 0

            prices = []



            for trade in records:


                price = float(

                    trade.get("price", 0)

                )


                quantity = float(

                    trade.get("quantity", 0)

                )


                total_volume += quantity


                money_volume += (

                    price *

                    quantity

                )


                prices.append(price)



            if not prices:

                continue



            current_price = prices[0]


            low = min(prices)

            high = max(prices)



            change_percent = (

                (current_price - low)

                /

                low

                *

                100

            ) if low else 0



            analysis = analyze_volume(

                ticker=ticker,

                price=current_price,

                volume=int(total_volume),

                average_volume=max(

                    int(total_volume / 2),

                    1

                ),

                change_percent=change_percent,

                low=low,

                high=high

            )



            analysis["trades"] = len(records)

            analysis["classCode"] = class_code

            analysis["money_volume_real"] = money_volume



            result.append(

                analysis

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


        for item in result[:10]:

            print(

                item["ticker"],

                "оборот:",

                round(

                    item["money_volume"],

                    2

                ),

                "score:",

                item["volume_score"],

                "signal:",

                item["signal"]

            )



        return result





if __name__ == "__main__":

    scanner = VolumeScanner()

    scanner.start()

