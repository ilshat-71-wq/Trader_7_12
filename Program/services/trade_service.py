from api.bcs_api import BCSAPI


class TradeService:

    def __init__(self):

        self.api = BCSAPI()

        self.api.authorize()

    def load(self, ticker, class_code):

        print(f"\nTradeService: {ticker} {class_code}")

        return self.api.get_last_trades(
            ticker,
            class_code
        )