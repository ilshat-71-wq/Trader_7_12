class RatingService:

    """
    Рассчитывает рейтинг бумаги.
    Чем выше рейтинг — тем выше бумага в сканере.
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
        # Денежный оборот
        # -----------------------------------

        if money_volume > 100_000_000:
            score += 50

        elif money_volume > 50_000_000:
            score += 40

        elif money_volume > 20_000_000:
            score += 30

        elif money_volume > 10_000_000:
            score += 20

        elif money_volume > 5_000_000:
            score += 10

        # -----------------------------------
        # Изменение цены
        # -----------------------------------

        if abs(change) >= 5:
            score += 30

        elif abs(change) >= 3:
            score += 20

        elif abs(change) >= 2:
            score += 10

        # -----------------------------------
        # Объем
        # -----------------------------------

        if volume > 1_000_000:
            score += 20

        elif volume > 500_000:
            score += 15

        elif volume > 100_000:
            score += 10

        elif volume > 50_000:
            score += 5

        return score