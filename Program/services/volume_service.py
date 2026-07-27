class VolumeService:

    @staticmethod
    def calc(last, trades):

        volume = 0

        if trades is None:
            return 0, 0

        records = trades.get("records", [])

        for trade in records:

            qty = trade.get("quantity", 0)

            volume += qty

        money = volume * last

        return volume, money