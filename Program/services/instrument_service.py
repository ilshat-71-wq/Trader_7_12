from api.bcs_api import BCSAPI


class InstrumentService:

    def __init__(self):

        self.api = BCSAPI()

    def connect(self):

        return self.api.authorize()

    def load_stocks(self):

        return self.api.get_instruments("STOCK")