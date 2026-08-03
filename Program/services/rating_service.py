class RatingService:

    """
    Профессиональный рейтинг бумаги.

    Чем выше рейтинг,
    тем интереснее инструмент для сканера.
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
        # 1. Денежный оборот
        # -----------------------------------

        if money_volume >= 1_000_000_000:
            score += 50

        elif money_volume >= 500_000_000:
            score += 45

        elif money_volume >= 100_000_000:
            score += 35

        elif money_volume >= 50_000_000:
            score += 25

        elif money_volume >= 10_000_000:
            score += 15

        elif money_volume >= 1_000_000:
            score += 5



        # -----------------------------------
        # 2. Сила движения цены
        # -----------------------------------

        abs_change = abs(change)


        if abs_change >= 5:
            score += 30

        elif abs_change >= 3:
            score += 25

        elif abs_change >= 2:
            score += 20

        elif abs_change >= 1:
            score += 10

        elif abs_change >= 0.5:
            score += 5



        # -----------------------------------
        # 3. Торговый объем
        # -----------------------------------

        if volume >= 10_000_000:
            score += 20

        elif volume >= 1_000_000:
            score += 15

        elif volume >= 100_000:
            score += 10

        elif volume >= 10_000:
            score += 5



        # -----------------------------------
        # 4. Бонус за сильный импульс
        # -----------------------------------

        if money_volume > 500_000_000 and abs_change > 2:
            score += 10


        return score