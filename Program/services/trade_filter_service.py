"""
Trader_7_12 Pro

Trade Filter Service

Версия 0.4

Назначение:

- финальный фильтр сделки
- контроль качества входа
- защита от слабых сигналов
- оценка торгового допуска
- отдельный допуск сильного EARLY momentum setup
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

        # -----------------------------------------------------
        # NO SIGNAL
        # -----------------------------------------------------

        if signal in (
            "NO_SIGNAL",
            None
        ):

            return {
                "allowed": False,
                "level": "BLOCK",
                "reason": "No signal"
            }

        # -----------------------------------------------------
        # EARLY MOMENTUM TRADE
        # -----------------------------------------------------
        #
        # Разрешаем ранний вход без подтверждённого breakout,
        # если momentum уже достаточно сильный и остальные
        # параметры setup подтверждены.
        #
        # LONG:
        #   momentum >= 60
        #
        # SHORT:
        #   momentum <= -60
        #
        # Breakout для этой ветки НЕ обязателен.
        # -----------------------------------------------------

        early_momentum_ok = (

            (
                signal == "EARLY_LONG"
                and momentum_score >= 60
            )

            or

            (
                signal == "EARLY_SHORT"
                and momentum_score <= -60
            )

        )

        if (
            early_momentum_ok
            and confidence >= 55
            and trade_score >= 55
            and volume_score >= 40
            and rr_ratio >= 2
        ):

            return {
                "allowed": True,
                "level": "EARLY_TRADE",
                "reason":
                    "Strong momentum early setup"
            }

        # -----------------------------------------------------
        # STRONG BREAKOUT TRADE
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # DEVELOPING BREAKOUT
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # BLOCK
        # -----------------------------------------------------

        return {

            "allowed": False,

            "level": "BLOCK",

            "reason":
                "Conditions not sufficient"

        }
