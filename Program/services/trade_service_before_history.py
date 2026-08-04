from api.bcs_api import BCSAPI


class TradeService:


    def __init__(self):

        self.api = BCSAPI()

        self.api.authorize()



    def load(self, ticker, class_code):


        print()

        print(
            f"TradeService: {ticker} {class_code}"
        )


        result = self.api.get_last_trades(

            ticker,

            class_code

        )


        print()

        print("========== RAW TRADES ==========")

        print(result)

        print("================================")



        return result