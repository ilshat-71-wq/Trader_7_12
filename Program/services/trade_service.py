from api.bcs_api import BCSAPI


class TradeService:

    def __init__(self):

        self.api = BCSAPI()
        self.api.authorize()

    def load(self, ticker, class_code):

        trades = self.api.get_last_trades(
            ticker=ticker,
            class_code=class_code
        )

        if not trades:
            return []

        return trades