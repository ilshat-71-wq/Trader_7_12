"""
Trader_7_12 Pro

Trade Decision Engine v0.8

Назначение:

- финальный отбор торговых возможностей
- фильтрация слабых сигналов
- пропуск только реальных торговых сигналов
- защита от TRADE при NO_SIGNAL
- проверка объема
- проверка согласованности направления
"""


class TradeDecisionEngine:

    def __init__(self):

        self.version = "0.8"


    # -------------------------------------------------
    # Главная проверка сделки
    # -------------------------------------------------

    def evaluate(
        self,
        row
    ):

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

        signal = getattr(
            row,
            "signal",
            ""
        )


        # -------------------------------------------------
        # 1. Направление обязательно
        # -------------------------------------------------

        if direction not in (
            "LONG",
            "SHORT"
        ):

            return {
                "decision": "SKIP",
                "reason": "No valid direction"
            }


        # -------------------------------------------------
        # 2. NO_SIGNAL не может быть TRADE
        # -------------------------------------------------

        active_signals = (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG",
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        )


        if signal not in active_signals:

            return {
                "decision": "SKIP",
                "reason": "No active signal"
            }


        # -------------------------------------------------
        # 3. Проверяем согласованность направления
        # -------------------------------------------------

        long_signals = (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG"
        )

        short_signals = (
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        )


        if signal in long_signals:

            if direction != "LONG":

                return {
                    "decision": "SKIP",
                    "reason": "Direction mismatch"
                }


        if signal in short_signals:

            if direction != "SHORT":

                return {
                    "decision": "SKIP",
                    "reason": "Direction mismatch"
                }


        # -------------------------------------------------
        # 4. Минимальный score
        # -------------------------------------------------

        if score < 35:

            return {
                "decision": "SKIP",
                "reason": "Low trade score"
            }


        # -------------------------------------------------
        # 5. Минимальный rating
        # -------------------------------------------------

        if rating < 40:

            return {
                "decision": "SKIP",
                "reason": "Low rating"
            }


        # -------------------------------------------------
        # 6. Минимальная ликвидность
        # -------------------------------------------------

        if money_volume < 3_000_000:

            return {
                "decision": "SKIP",
                "reason": "Low liquidity"
            }


        # -------------------------------------------------
        # 7. Расширение объема
        # -------------------------------------------------

        if volume_ratio < 1.2:

            return {
                "decision": "SKIP",
                "reason": "No volume expansion"
            }


        # -------------------------------------------------
        # 8. Проверка momentum
        # -------------------------------------------------

        if direction == "LONG":

            if momentum < 45:

                return {
                    "decision": "SKIP",
                    "reason": "Weak long momentum"
                }


        if direction == "SHORT":

            if momentum > -45:

                return {
                    "decision": "SKIP",
                    "reason": "Weak short momentum"
                }


        # -------------------------------------------------
        # Подтверждения
        # -------------------------------------------------

        reasons = []


        if direction == "LONG":

            reasons.append(
                "Positive momentum"
            )


        elif direction == "SHORT":

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


        elif volume_ratio >= 1.2:

            reasons.append(
                "Volume expansion"
            )


        # -------------------------------------------------
        # Confidence
        # -------------------------------------------------

        confidence = "LOW"


        if score >= 80:

            confidence = "HIGH"

        elif score >= 60:

            confidence = "MEDIUM"


        # -------------------------------------------------
        # Финальное решение
        # -------------------------------------------------

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

            "signal":
                signal,

            "trade_score":
                score,

            "rating":
                rating,

            "momentum_score":
                momentum,

            "volume_ratio":
                volume_ratio,

            "money_volume":
                money_volume,

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

            key=lambda x: (

                x.get(
                    "trade_score",
                    0
                ),

                x.get(
                    "momentum_score",
                    0
                ),

                x.get(
                    "rating",
                    0
                )

            ),

            reverse=True

        )


        return results
