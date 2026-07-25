from market.market_loader import MarketLoader


class Engine:

    def __init__(self):

        self.loader = MarketLoader()

        self.market = {}

    def update(self):

        # Пока здесь будут тестовые данные.
        # Следующим шагом заменим на реальные данные БКС.

        self.market = {
            "SBER": {
                "price": 264.50,
                "volume": 58234,
                "turnover": 264.50 * 58234,
            },
            "SI": {
                "price": 79850,
                "volume": 183452,
                "turnover": 79850 * 183452,
            },
            "IMOEX": {
                "price": 2025,
                "volume": 95000,
                "turnover": 2025 * 95000,
            },
            "LKOH": {
                "price": 6712.0,
                "volume": 12350,
                "turnover": 6712.0 * 12350,
            },
            "GOLD": {
                "price": 86540,
                "volume": 17420,
                "turnover": 86540 * 17420,
            },
        }

    def get_market(self):

        return self.market