"""
Trader_7_12 Pro

Trade Filter Service

Версия 0.3

Назначение:
- финальный фильтр сделки
- контроль качества входа
- защита от слабых сигналов
- оценка торгового допуска
"""


class TradeFilterService:


    def check(
        self,
        signal,
        confidence,
        breakout_quality=0,
        trade_score=0,
        rr_ratio=0,
        breakout_score=0,
        momentum_score=0,
        volume_score=0
    ):


        if signal in (
            "NO_SIGNAL",
            None
        ):

            return {

                "allowed": False,

                "level": "BLOCK",

                "reason": "No signal"

            }



        if (

            confidence >= 80

            and breakout_quality >= 60

            and breakout_score >= 60

            and trade_score >= 75

            and volume_score >= 60

            and rr_ratio >= 2

        ):

            return {

                "allowed": True,

                "level": "STRONG_TRADE",

                "reason":
                    "High quality breakout setup"

            }



        if (

            confidence >= 55

            and breakout_score >= 30

            and trade_score >= 50

            and volume_score >= 40

            and rr_ratio >= 1.5

        ):

            return {

                "allowed": True,

                "level": "WATCHLIST",

                "reason":
                    "Setup developing"

            }



        return {

            "allowed": False,

            "level": "BLOCK",

            "reason":
                "Conditions not sufficient"

        }
