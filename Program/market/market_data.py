"""
Trader_7_12 Pro

Market Data

Версия 0.1

Назначение:
- подготовка данных рынка
- преобразование данных BCS API
- передача в сканер
"""


from market.market_loader import MarketLoader





class MarketData:


    def __init__(self):

        self.loader = MarketLoader()

        self.instruments = []



    def connect(self):

        return self.loader.connect()



    def update(self):

        """
        Получение данных рынка
        """


        data = self.loader.load()


        if data is None:

            print(
                "⚠️ Нет данных рынка"
            )

            return []



        self.instruments = (
            self.prepare_instruments(data)
        )


        return self.instruments




    def prepare_instruments(
            self,
            data
    ):

        """
        Приводим данные БКС
        к формату сканера
        """


        result = []



        for item in data:


            instrument = {


                "ticker":
                item.get(
                    "ticker",
                    "UNKNOWN"
                ),


                "price":
                item.get(
                    "lastPrice",
                    0
                ),


                "volume":
                item.get(
                    "volume",
                    0
                ),


                "average_volume":
                item.get(
                    "averageVolume",
                    1
                )

            }


            result.append(
                instrument
            )



        return result