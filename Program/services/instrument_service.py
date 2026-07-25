from api.bcs_api import BCSAPI


class InstrumentService:

    def __init__(self):
        self.api = BCSAPI()
        self.instruments = {}

    def load(self):

        if not self.api.authorize():
            return False

        types = [
            "STOCK",
            "FUTURES",
            "CURRENCY",
            "INDEX"
        ]

        for t in types:

            print(f"Загрузка {t}...")

            data = self.api.get_instruments(t)

            if data:
                self.instruments[t] = data
                print(f"{t}: {len(data)} инструментов")

        return True

    def get(self, instrument_type):

        return self.instruments.get(instrument_type, [])