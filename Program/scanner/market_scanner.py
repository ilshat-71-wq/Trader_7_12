"""
Trader_7_12 Pro

Market Scanner

Версия 0.2

Назначение:
- анализ списка инструментов
- Volume x Price анализ
- расчет профессионального рейтинга
- формирование TOP кандидатов
"""


from scanner.volume_price import analyze_volume

from services.rating_service import RatingService



class MarketScanner:


    def __init__(self):

        self.results = []

        self.rating_service = RatingService()



    def scan(
            self,
            instruments
    ):

        """
        Анализ рынка

        instruments:

        {
            ticker,
            price,
            volume,
            average_volume,

            change_percent,
            low,
            high
        }

        """


        self.results = []


        for item in instruments:


            volume_result = analyze_volume(

                ticker=item["ticker"],

                price=item["price"],

                volume=item["volume"],

                average_volume=item["average_volume"],

                change_percent=item.get(
                    "change_percent",
                    0
                ),

                low=item.get(
                    "low",
                    0
                ),

                high=item.get(
                    "high",
                    0
                )

            )



            rating = self.rating_service.calculate(

                last=item["price"],

                change=item.get(
                    "change_percent",
                    0
                ),

                volume=item["volume"],

                money_volume=volume_result["money_volume"]

            )



            volume_result["rating"] = rating



            self.results.append(
                volume_result
            )



        self.results.sort(

            key=lambda x: x["rating"],

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