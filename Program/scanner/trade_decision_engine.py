"""
Trader_7_12 Pro

Trade Decision Engine v0.7

Назначение:
- финальный отбор торговых возможностей
- фильтрация слабых сигналов
- поиск лучших торговых идей
"""


class TradeDecisionEngine:


    def __init__(self):

        self.version = "0.7"



    # -------------------------------------------------
    # Главная проверка сделки
    # -------------------------------------------------

    def evaluate(
        self,
        row
    ):

        reasons = []


        score = getattr(
            row,
            "trade_score",
            0
        )


        rating = getattr(
            row,
            "rating",
            0
        )


        momentum = getattr(
            row,
            "momentum_score",
            0
        )


        money_volume = getattr(
            row,
            "money_volume",
            0
        )


        volume_ratio = getattr(
            row,
            "volume_ratio",
            0
        )


        direction = getattr(
            row,
            "direction",
            ""
        )



        # -----------------------------
        # Базовые фильтры
        # -----------------------------

        if not direction:

            return {
                "decision": "SKIP",
                "reason": "No direction"
            }



        if score < 35:

            return {
                "decision": "SKIP",
                "reason": "Low trade score"
            }



        if rating < 40:

            return {
                "decision": "SKIP",
                "reason": "Low rating"
            }



        if money_volume < 3_000_000:

            return {
                "decision": "SKIP",
                "reason": "Low liquidity"
            }



        if volume_ratio < 1.2:

            return {
                "decision": "SKIP",
                "reason": "No volume expansion"
            }



        # -----------------------------
        # Подтверждения
        # -----------------------------

        if momentum >= 45:

            reasons.append(
                "Positive momentum"
            )


        elif momentum <= -45:

            reasons.append(
                "Negative momentum"
            )


        if money_volume >= 10_000_000:

            reasons.append(
                "Strong liquidity"
            )


        if volume_ratio >= 2:

            reasons.append(
                "Volume spike"
            )



        confidence = "LOW"


        if score >= 80:

            confidence = "HIGH"


        elif score >= 60:

            confidence = "MEDIUM"



        return {


            "decision":

                "TRADE",


            "ticker":

                getattr(
                    row,
                    "ticker",
                    ""
                ),


            "direction":

                direction,


            "trade_score":

                score,


            "rating":

                rating,


            "confidence":

                confidence,


            "reasons":

                reasons

        }



    # -------------------------------------------------
    # Массовая обработка
    # -------------------------------------------------

    def rank(
        self,
        rows
    ):


        results = []


        for row in rows:

            result = self.evaluate(
                row
            )


            if result.get(
                "decision"
            ) == "TRADE":

                results.append(
                    result
                )



        results.sort(

            key=lambda x:

            x.get(
                "trade_score",
                0
            ),

            reverse=True

        )


        return results
