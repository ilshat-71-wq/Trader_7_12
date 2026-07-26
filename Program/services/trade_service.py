from api.bcs_api import BCSAPI


class TradeService:

    def __init__(self):
        self.api = BCSAPI()

    def connect(self):
        return self.api.authorize()

    def get(self, ticker, class_code="TQBR", limit=100):

        instruments = [
            {
                "ticker": ticker,
                "classCode": class_code
            }
        ]

        return self.api.get_last_trades(instruments, limit)