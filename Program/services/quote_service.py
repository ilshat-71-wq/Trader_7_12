from api.bcs_api import BCSAPI


class QuoteService:

    def __init__(self):

        self.api = BCSAPI()

        self.quotes = {}

    def connect(self):

        return self.api.authorize()

    def update(self, ticker):

        """
        Пока заглушка.

        Следующим релизом здесь будет настоящий запрос
        последней цены из API БКС.
        """

        self.quotes[ticker] = {
            "ticker": ticker,
            "price": 0,
            "volume": 0,
            "price_volume": 0
        }

        return self.quotes[ticker]

    def get(self, ticker):

        return self.quotes.get(ticker)