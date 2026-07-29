class VolumeEngine:

    def __init__(self):

        self.version = "0.1"


    # ---------------------------------------------------------

    def calculate_flow(self, trades):

        """
        Расчёт денежного потока.

        Пока БКС отдаёт только список сделок.
        Готовим архитектуру под:
        цена × объём
        """

        total_volume = 0
        total_money = 0
        buy_volume = 0
        sell_volume = 0


        for trade in trades:

            price = trade.get(
                "price",
                0
            )

            volume = trade.get(
                "quantity",
                0
            )


            money = (
                price *
                volume
            )


            total_volume += volume
            total_money += money


            side = trade.get(
                "side",
                ""
            )


            if side == "BUY":

                buy_volume += volume


            elif side == "SELL":

                sell_volume += volume



        return {

            "volume":
                total_volume,

            "money":
                round(
                    total_money,
                    2
                ),

            "buy_volume":
                buy_volume,

            "sell_volume":
                sell_volume

        }



    # ---------------------------------------------------------

    def analyze(self, ticker, trades):

        flow = self.calculate_flow(
            trades
        )


        return {

            "ticker":
                ticker,

            "volume":
                flow["volume"],

            "money":
                flow["money"],

            "buy":
                flow["buy_volume"],

            "sell":
                flow["sell_volume"]

        }



    # ---------------------------------------------------------

    def print_report(self, data):

        print()

        print(
            "====== VOLUME ENGINE ======"
        )


        print(
            f"{data['ticker']}"
        )

        print(
            "Объём:",
            data["volume"]
        )

        print(
            "Деньги:",
            data["money"]
        )

        print(
            "BUY:",
            data["buy"]
        )

        print(
            "SELL:",
            data["sell"]
        )



# ---------------------------------------------------------


if __name__ == "__main__":

    engine = VolumeEngine()


    test_trades = [

        {
            "price": 100,
            "quantity": 5,
            "side": "BUY"
        },

        {
            "price": 101,
            "quantity": 3,
            "side": "SELL"
        }

    ]


    result = engine.analyze(
        "TEST",
        test_trades
    )


    engine.print_report(
        result
    )