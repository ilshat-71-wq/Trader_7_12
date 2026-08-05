"""
Trader_7_12 Pro

Trade Ranker Service

Версия 0.1

Назначение:
- выбор лучших торговых идей
- фильтрация слабых сигналов
- сортировка по качеству
- подготовка TOP кандидатов
"""


class TradeRankerService:


    def rank(self, items, limit=3):

        ranked = []


        for item in items:

            signal = item.get(
                "signal",
                item.get(
                    "final_signal",
                    "NO_SIGNAL"
                )
            )


            confidence = item.get(
                "confidence",
                0
            )


            rr = item.get(
                "rr",
                item.get(
                    "rr_ratio",
                    0
                )
            )


            if signal == "NO_SIGNAL":
                continue


            if confidence < 55:
                continue


            if rr and rr < 2:
                continue


            ranked.append(item)



        ranked.sort(

            key=lambda x: (

                x.get(
                    "confidence",
                    0
                ),

                x.get(
                    "trade_score",
                    {}
                ).get(
                    "trade_score",
                    0
                )
                if isinstance(
                    x.get("trade_score"),
                    dict
                )
                else x.get(
                    "trade_score",
                    0
                ),

                x.get(
                    "rr",
                    x.get(
                        "rr_ratio",
                        0
                    )
                )

            ),

            reverse=True

        )


        return ranked[:limit]
