from api.bcs_api import BCSAPI


class QuoteService:

    def __init__(self):

        self.api = BCSAPI()

        if self.api.access_token is None:
            self.api.authorize()

    # ---------------------------------------------------------

    def load(self, ticker, class_code):

        quotes = self.api.get_quotes(
            [
                {
                    "ticker": ticker,
                    "classCode": class_code
                }
            ]
        )

        if not quotes:
            return None

        return quotes