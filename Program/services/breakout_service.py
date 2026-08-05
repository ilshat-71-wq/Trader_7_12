"""
Trader_7_12 Pro

Breakout Service

Версия 0.2

Назначение:
- анализ пробоя уровней
- поиск развития движения
- оценка силы пробоя
"""


class BreakoutService:


    def analyze(
        self,
        current_price,
        previous_high=None,
        previous_low=None,
        volume_ratio=0
    ):

        score = 0

        direction = "NO_SIGNAL"

        breakout = False

        state = "NO_SIGNAL"


        # -----------------------------
        # CONFIRMED BREAKOUT
        # -----------------------------

        if previous_high and current_price > previous_high:

            breakout = True

            direction = "LONG"

            state = "CONFIRMED"

            score += 50


        elif previous_low and current_price < previous_low:

            breakout = True

            direction = "SHORT"

            state = "CONFIRMED"

            score += 50


        # -----------------------------
        # DEVELOPING BREAKOUT
        # -----------------------------

        elif previous_high:

            distance = current_price / previous_high

            if distance >= 0.995:

                direction = "LONG"

                state = "DEVELOPING"

                score += 25


        elif previous_low:

            distance = current_price / previous_low

            if distance <= 1.005:

                direction = "SHORT"

                state = "DEVELOPING"

                score += 25


        # -----------------------------
        # VOLUME CONFIRMATION
        # -----------------------------

        if volume_ratio >= 5:

            score += 30


        elif volume_ratio >= 3:

            score += 20


        elif volume_ratio >= 2:

            score += 10



        return {

            "breakout": breakout,

            "direction": direction,

            "breakout_state": state,

            "breakout_score": min(
                score,
                100
            )

        }
