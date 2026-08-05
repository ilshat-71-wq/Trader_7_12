"""
Trader_7_12 Pro

Volume Score Service

Версия 0.2

Назначение:
- анализ силы объёма
- volume ratio
- money flow
- объёмный рейтинг PRO
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



        # ---------------------------------
        # Volume strength PRO
        # ---------------------------------

        if volume_ratio >= 5:

            volume_score += 100

        elif volume_ratio >= 3:

            volume_score += 85

        elif volume_ratio >= 2:

            volume_score += 70

        elif volume_ratio >= 1.5:

            volume_score += 50

        elif volume_ratio >= 1:

            volume_score += 30

        else:

            volume_score += 0



        # ---------------------------------
        # Money flow strength PRO
        # ---------------------------------

        money_score = 0


        if money_ratio >= 5:

            money_score = 100

        elif money_ratio >= 3:

            money_score = 85

        elif money_ratio >= 2:

            money_score = 70

        elif money_ratio >= 1.5:

            money_score = 50

        elif money_ratio >= 1:

            money_score = 30

        else:

            money_score = 0



        # ---------------------------------
        # Итоговый объёмный рейтинг
        # ---------------------------------

        final_score = (
            volume_score * 0.6
            +
            money_score * 0.4
        )


        if final_score > 100:

            final_score = 100



        return {


            "volume_score": round(
                final_score,
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
