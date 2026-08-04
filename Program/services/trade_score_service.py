"""
Trader_7_12 Pro

Trade Score Service

Версия 0.1

Назначение:
- итоговый торговый рейтинг
- объединение объёма
- импульса
- сигнала
"""


class TradeScoreService:


    def calculate(
        self,
        volume_score=0,
        momentum_score=0,
        signal="NO_SIGNAL"
    ):

        signal_bonus = 0


        if signal in (
            "STRONG_LONG",
            "STRONG_SHORT"
        ):

            signal_bonus = 100


        elif signal in (
            "LONG_WATCH",
            "SHORT_WATCH"
        ):

            signal_bonus = 50



        score = (

            volume_score * 0.5

            +

            abs(momentum_score) * 0.3

            +

            signal_bonus * 0.2

        )


        return round(
            score,
            2
        )
