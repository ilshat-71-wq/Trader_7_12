class Scanner:

    def __init__(self):

        self.market = {}

    def update_symbol(self, symbol, price, volume):

        self.market[symbol] = {
            "price": price,
            "volume": volume,
            "turnover": price * volume
        }

    def get_market(self):

        return self.market