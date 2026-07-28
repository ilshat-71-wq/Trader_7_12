class RatingService:

    @staticmethod
    def calc(
        change,
        money_volume,
        volume
    ):
        """
        Расчёт рейтинга бумаги.

        Пока используем простую формулу.
        Далее будем усложнять.

        Вес:
            Money Volume
            Изменение цены
            Объём сделок
        """

        rating = 0

        #
        # Денежный объём
        #
        rating += money_volume

        #
        # Изменение цены
        #
        rating += abs(change) * 100000

        #
        # Объём
        #
        rating += volume * 10

        return rating