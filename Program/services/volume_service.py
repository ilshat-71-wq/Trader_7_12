class VolumeService:

    @staticmethod
    def calculate(trades):

        if trades is None:
            return 0

        total = 0

        records = trades.get("records", [])

        for instrument in records:

            for trade in instrument.get("trades", []):

                qty = trade.get("quantity", 0)

                total += qty

        return total