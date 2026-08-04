"""
Trader_7_12 Pro

Breakout Service

Версия 0.1

Назначение:
- анализ пробоя уровней
- определение направления
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


        if previous_high and current_price > previous_high:

            breakout = True
            direction = "LONG"

            score += 50


        elif previous_low and current_price < previous_low:

            breakout = True
            direction = "SHORT"

            score += 50



        if volume_ratio >= 2:

            score += 30

        elif volume_ratio >= 1.5:

            score += 20



        return {

            "breakout": breakout,

            "direction": direction,

            "breakout_score": min(
                score,
                100
            )

        }