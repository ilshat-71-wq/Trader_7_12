"""
Trader_7_12 Pro

Trade Score Service

Версия 0.2

Назначение:
- итоговый торговый рейтинг
- баланс объёма
- импульс
- пробой
- сила сигнала
"""


class TradeScoreService:


    def calculate(
        self,
        volume_score=0,
        momentum_score=0,
        breakout_score=0,
        signal="NO_SIGNAL"
    ):


        signal_score = 0


        if signal in (
            "STRONG_LONG",
            "STRONG_SHORT"
        ):

            signal_score = 100


        elif signal in (
            "LONG_WATCH",
            "SHORT_WATCH"
        ):

            signal_score = 70


        elif signal in (
            "EARLY_LONG",
            "EARLY_SHORT"
        ):

            signal_score = 50


        score = (

            volume_score * 0.30

            +

            abs(momentum_score) * 0.30

            +

            breakout_score * 0.25

            +

            signal_score * 0.15

        )


        if score > 100:

            score = 100


        if score >= 90:

            grade = "TRADE_READY"


        elif score >= 75:

            grade = "WATCH"


        elif score >= 50:

            grade = "DEVELOPING"


        else:

            grade = "IGNORE"



        return {

            "trade_score": round(
                score,
                2
            ),

            "trade_grade": grade

        }
