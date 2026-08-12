"""
Trader_7_12 Pro

Money Flow Service

Версия 0.1

Назначение:

- анализ денежного оборота инструмента
- сравнение текущего оборота с историческим baseline
- определение силы денежной активности
- подготовка данных для Market Leader Engine

ВАЖНО:

money_volume показывает абсолютную ликвидность.

money_ratio показывает относительную активность:

    текущий оборот / нормальный оборот

money_activity_score показывает силу текущей денежной активности
по шкале 0-100.
"""


class MoneyFlowService:

    def calculate(
        self,
        money_volume=0,
        average_money_volume=0
    ):

        try:
            money_volume = float(
                money_volume or 0
            )
        except (
            TypeError,
            ValueError
        ):
            money_volume = 0.0

        try:
            average_money_volume = float(
                average_money_volume or 0
            )
        except (
            TypeError,
            ValueError
        ):
            average_money_volume = 0.0

        # -----------------------------------------------------
        # MONEY RATIO
        # -----------------------------------------------------

        money_ratio = 0.0

        if average_money_volume > 0:

            money_ratio = (
                money_volume /
                average_money_volume
            )

        # -----------------------------------------------------
        # MONEY ACTIVITY SCORE
        # -----------------------------------------------------
        #
        # Оцениваем не абсолютный размер оборота,
        # а насколько текущая активность выше нормы.
        #
        # < 0.75       -> очень слабая
        # < 1.00       -> слабая
        # 1.00-1.49    -> нормальная
        # 1.50-1.99    -> повышенная
        # 2.00-2.99    -> сильная
        # 3.00-4.99    -> очень сильная
        # >= 5.00      -> экстремальная
        # -----------------------------------------------------

        if money_ratio >= 5:

            money_activity_score = 100

        elif money_ratio >= 3:

            money_activity_score = 90

        elif money_ratio >= 2:

            money_activity_score = 80

        elif money_ratio >= 1.5:

            money_activity_score = 65

        elif money_ratio >= 1:

            money_activity_score = 50

        elif money_ratio >= 0.75:

            money_activity_score = 30

        else:

            money_activity_score = 15

        # -----------------------------------------------------
        # MONEY ACTIVITY STATE
        # -----------------------------------------------------

        if money_ratio >= 3:

            money_activity_state = (
                "EXTREME"
            )

        elif money_ratio >= 2:

            money_activity_state = (
                "STRONG"
            )

        elif money_ratio >= 1.5:

            money_activity_state = (
                "ELEVATED"
            )

        elif money_ratio >= 1:

            money_activity_state = (
                "NORMAL"
            )

        elif money_ratio >= 0.75:

            money_activity_state = (
                "WEAK"
            )

        else:

            money_activity_state = (
                "VERY_WEAK"
            )

        return {

            "money_volume": round(
                money_volume,
                2
            ),

            "average_money_volume": round(
                average_money_volume,
                2
            ),

            "money_ratio": round(
                money_ratio,
                2
            ),

            "money_activity_score": (
                money_activity_score
            ),

            "money_activity_state": (
                money_activity_state
            )

        }
