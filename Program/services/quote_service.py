from api.bcs_api import BCSAPI


class QuoteService:

    def __init__(self):

        self.api = BCSAPI()

        if self.api.access_token is None:
            self.api.authorize()

    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code
    ):

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

        #
        # API БКС возвращает список
        #
        if isinstance(quotes, list):

            if len(quotes) == 0:
                return None

            quote = quotes[0]

        #
        # Иногда приходит {"records":[...]}
        #
        elif isinstance(quotes, dict):

            records = quotes.get("records", [])

            if not records:
                return None

            quote = records[0]

        else:

            return None

        #
        # Для диагностики
        #
        print()
        print("========== RAW QUOTE ==========")
        print(quote)
        print("===============================")
        print()

        return quote