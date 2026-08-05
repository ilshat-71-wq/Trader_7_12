"""
Trader_7_12 Pro

Breakout Quality Service

Версия 0.1

Назначение:
- оценка качества пробоя
- фильтрация ложных пробоев
- анализ свечного подтверждения
"""


class BreakoutQualityService:


    def analyze(
        self,
        current_price,
        open_price,
        high_price,
        low_price,
        close_price,
        previous_high=None,
        previous_low=None
    ):

        score = 0

        reasons = []


        # -----------------------------
        # Свеча
        # -----------------------------

        body = abs(
            close_price - open_price
        )


        candle_range = (
            high_price - low_price
        )


        body_ratio = 0


        if candle_range > 0:

            body_ratio = body / candle_range



        # сильное тело свечи

        if body_ratio >= 0.6:

            score += 25

            reasons.append(
                "Strong candle body"
            )


        elif body_ratio >= 0.4:

            score += 15



        # -----------------------------
        # LONG breakout quality
        # -----------------------------

        if previous_high:

            if close_price > previous_high:

                score += 35

                reasons.append(
                    "Close above breakout level"
                )


        # -----------------------------
        # SHORT breakout quality
        # -----------------------------

        if previous_low:

            if close_price < previous_low:

                score += 35

                reasons.append(
                    "Close below breakdown level"
                )



        # -----------------------------
        # Маленькие тени
        # -----------------------------

        upper_shadow = (
            high_price -
            max(open_price, close_price)
        )


        lower_shadow = (
            min(open_price, close_price)
            -
            low_price
        )


        if body > 0:


            if upper_shadow / body < 0.5:

                score += 10


            if lower_shadow / body < 0.5:

                score += 10



        return {

            "breakout_quality_score": min(
                score,
                100
            ),

            "breakout_quality_reasons": reasons

        }
