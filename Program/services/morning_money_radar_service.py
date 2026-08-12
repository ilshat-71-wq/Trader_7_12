"""
Trader_7_12 Pro

Morning Money Radar Service
Версия 1.0

Назначение:
- расчёт фактического денежного оборота текущей утренней сессии
- сравнение с нормальным средним дневным оборотом
- определение аномальной денежной активности
"""


class MorningMoneyRadarService:

    def calculate(
        self,
        morning_money_volume=0,
        average_daily_money_volume=0,
    ):

        morning_money_volume = float(
            morning_money_volume or 0
        )

        average_daily_money_volume = float(
            average_daily_money_volume or 0
        )

        # -----------------------------------------------------
        # DAILY MONEY RATIO
        # -----------------------------------------------------

        if average_daily_money_volume > 0:

            daily_money_ratio = (
                morning_money_volume
                / average_daily_money_volume
            )

        else:

            daily_money_ratio = 0

        # -----------------------------------------------------
        # MONEY ACTIVITY SCORE
        # -----------------------------------------------------

        if daily_money_ratio >= 3:

            money_activity_score = 100

        elif daily_money_ratio >= 2:

            money_activity_score = 90

        elif daily_money_ratio >= 1.5:

            money_activity_score = 80

        elif daily_money_ratio >= 1:

            money_activity_score = 60

        elif daily_money_ratio >= 0.75:

            money_activity_score = 40

        else:

            money_activity_score = 20

        # -----------------------------------------------------
        # MONEY ACTIVITY STATE
        # -----------------------------------------------------

        if daily_money_ratio >= 3:

            money_activity_state = "EXTREME"

        elif daily_money_ratio >= 2:

            money_activity_state = "STRONG"

        elif daily_money_ratio >= 1.5:

            money_activity_state = "ELEVATED"

        elif daily_money_ratio >= 1:

            money_activity_state = "NORMAL"

        elif daily_money_ratio >= 0.75:

            money_activity_state = "WEAK"

        else:

            money_activity_state = "VERY_WEAK"

        return {

            "morning_money_volume": round(
                morning_money_volume,
                2
            ),

            "average_daily_money_volume": round(
                average_daily_money_volume,
                2
            ),

            "daily_money_ratio": round(
                daily_money_ratio,
                2
            ),

            "money_activity_score": (
                money_activity_score
            ),

            "money_activity_state": (
                money_activity_state
            ),

        }

    # -----------------------------------------------------
    # AVERAGE DAILY MONEY VOLUME
    # -----------------------------------------------------

    def calculate_average_daily_money(
        self,
        daily_money_volumes
    ):
        """
        Средний дневной денежный оборот
        по завершённым торговым дням.
        """

        if not daily_money_volumes:
            return 0

        values = []

        for value in daily_money_volumes:

            try:
                value = float(value or 0)

                if value > 0:
                    values.append(value)

            except (TypeError, ValueError):
                continue

        if not values:
            return 0

        return round(
            sum(values) / len(values),
            2
        )

