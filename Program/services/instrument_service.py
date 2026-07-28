from api.bcs_api import BCSAPI


class InstrumentService:

    def __init__(self):

        self.api = BCSAPI()

    # ---------------------------------------------------------

    def connect(self):

        return self.api.authorize()

    # ---------------------------------------------------------

    def load_stocks(self):

        instruments = self.api.get_instruments("STOCK")

        if not instruments:
            return []

        result = []

        seen = set()

        for instrument in instruments:

            ticker = instrument.get("ticker")

            if not ticker:
                continue

            #
            # Убираем дубли по тикеру
            #
            if ticker in seen:
                continue

            seen.add(ticker)

            result.append(
                {
                    "ticker": ticker,
                    "classCode": "TQBR",
                    "shortName": instrument.get("shortName", ""),
                    "lotSize": instrument.get("lotSize", 1),
                    "sector": instrument.get("businessSector", "")
                }
            )

        print(f"Уникальных акций: {len(result)}")

        return result