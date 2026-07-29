"""
Trader_7_12 Pro

Market Scanner

Версия 0.1

Назначение:
- анализ списка инструментов
- расчет Volume x Price
- формирование рейтинга
"""


from scanner.volume_price import analyze_volume





class MarketScanner:


    def __init__(self):

        self.results = []



    def scan(self, instruments):

        """
        Анализ рынка

        instruments:
        список словарей:

        {
            ticker,
            price,
            volume,
            average_volume
        }

        """


        self.results = []


        for item in instruments:


            result = analyze_volume(

                ticker=item["ticker"],

                price=item["price"],

                volume=item["volume"],

                average_volume=item["average_volume"]

            )


            self.results.append(
                result
            )



        self.results.sort(

            key=lambda x: x["volume_score"],

            reverse=True

        )


        return self.results



    def get_top(
            self,
            count=5
    ):

        """
        Возвращает лучшие инструменты
        """

        return self.results[:count]