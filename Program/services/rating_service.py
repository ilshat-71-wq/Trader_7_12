class RatingService:

    """
    Trader_7_12 Pro

    Rating Engine v2

    Оценка инструмента:

    Liquidity  - ликвидность
    Momentum   - движение цены
    Volume     - активность
    Impulse    - сильный импульс

    Максимум: 100 баллов
    """

    def calculate(
        self,
        last: float,
        change: float,
        volume: float,
        money_volume: float,
    ) -> int:


        score = 0


        # -----------------------------------
        # 1. Liquidity
        # Денежный оборот
        # максимум 30
        # -----------------------------------

        if money_volume >= 1_000_000_000:
            score += 30

        elif money_volume >= 500_000_000:
            score += 25

        elif money_volume >= 100_000_000:
            score += 20

        elif money_volume >= 50_000_000:
            score += 15

        elif money_volume >= 10_000_000:
            score += 10

        elif money_volume >= 1_000_000:
            score += 5



        # -----------------------------------
        # 2. Momentum
        # Движение цены
        # максимум 25
        # -----------------------------------

        abs_change = abs(change)


        if abs_change >= 5:
            score += 25

        elif abs_change >= 3:
            score += 20

        elif abs_change >= 2:
            score += 15

        elif abs_change >= 1:
            score += 10

        elif abs_change >= 0.5:
            score += 5



        # -----------------------------------
        # 3. Volume
        # Торговая активность
        # максимум 25
        # -----------------------------------

        if volume >= 10_000_000:
            score += 25

        elif volume >= 1_000_000:
            score += 20

        elif volume >= 100_000:
            score += 15

        elif volume >= 10_000:
            score += 10

        elif volume > 0:
            score += 5



        # -----------------------------------
        # 4. Impulse
        # Сильное движение с деньгами
        # максимум 20
        # -----------------------------------

        if money_volume >= 500_000_000 and abs_change >= 3:
            score += 20

        elif money_volume >= 100_000_000 and abs_change >= 2:
            score += 15

        elif money_volume >= 50_000_000 and abs_change >= 1:
            score += 10



        # ограничение безопасности

        if score > 100:
            score = 100


        return score



    # -----------------------------------
    # Направление сделки
    # -----------------------------------

    def get_direction(
        self,
        change: float
    ) -> str:


        if change > 0:
            return "LONG"


        elif change < 0:
            return "SHORT"


        return "NEUTRAL"