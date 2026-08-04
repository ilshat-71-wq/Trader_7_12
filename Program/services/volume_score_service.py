"""
Trader_7_12 Pro

Volume Score Service

Версия 0.1

Назначение:
- анализ силы объёма
- volume ratio
- money flow
- объёмный рейтинг
"""


class VolumeScoreService:


    def calculate(
        self,
        volume=0,
        average_volume=0,
        money_volume=0,
        average_money_volume=0
    ):

        volume_ratio = 0

        money_ratio = 0


        if average_volume > 0:

            volume_ratio = volume / average_volume


        if average_money_volume > 0:

            money_ratio = money_volume / average_money_volume



        volume_score = 0



        # -------------------------------
        # Volume strength
        # -------------------------------

        if volume_ratio >= 3:

            volume_score += 60

        elif volume_ratio >= 2:

            volume_score += 45

        elif volume_ratio >= 1.5:

            volume_score += 30

        elif volume_ratio >= 1:

            volume_score += 20

        else:

            volume_score += 10



        # -------------------------------
        # Money flow strength
        # -------------------------------

        if money_ratio >= 3:

            volume_score += 40

        elif money_ratio >= 2:

            volume_score += 30

        elif money_ratio >= 1.5:

            volume_score += 20

        elif money_ratio >= 1:

            volume_score += 10



        if volume_score > 100:

            volume_score = 100



        return {

            "volume_score": round(
                volume_score,
                2
            ),

            "volume_ratio": round(
                volume_ratio,
                2
            ),

            "money_ratio": round(
                money_ratio,
                2
            )

        }
