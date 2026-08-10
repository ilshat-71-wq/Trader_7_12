from api.bcs_api import BCSAPI


class InstrumentLoader:

    def __init__(self):

        self.api = BCSAPI()

    # ---------------------------------------------------------
    # ACTIVE CONTRACTS
    # ---------------------------------------------------------

    def get_active_contracts(self):

        return self.load()

    # ---------------------------------------------------------
    # LOAD
    # ---------------------------------------------------------

    def load(self):

        print("📚 Загрузка ближайших фьючерсов")

        if not self.api.authorize():

            return []

        futures = self.api.get_instruments(
            "FUTURES"
        )

        print(
            "Всего фьючерсов:",
            len(futures)
        )

        instruments = []

        for item in futures:

            ticker = item.get(
                "ticker",
                ""
            )

            name = item.get(
                "shortName",
                ""
            )

            display = item.get(
                "displayName",
                ""
            )

            text = (
                ticker
                + " "
                + name
                + " "
                + display
            ).upper()

            asset = None

            # -------------------------------------------------
            # BRENT
            # -------------------------------------------------

            if "BR" in text:

                asset = "BR"

            # -------------------------------------------------
            # SI
            # -------------------------------------------------

            elif (
                "MTSI" in text
                or ticker.startswith("SI")
            ):

                asset = "SI"

            # -------------------------------------------------
            # GOLD
            # -------------------------------------------------

            elif "GOLD" in text:

                asset = "GOLD"

            # -------------------------------------------------
            # IMOEX
            # -------------------------------------------------

            elif (
                "IMOEX" in text
                or "ИНДЕКС МОСБИРЖИ" in text
            ):

                asset = "IMOEX"

            # -------------------------------------------------
            # MX
            # -------------------------------------------------

            elif "MX" in text:

                asset = "MX"

            if not asset:

                continue

            boards = item.get(
                "boards",
                []
            )

            class_code = ""

            if boards:

                class_code = boards[0].get(
                    "classCode",
                    ""
                )

            instruments.append(
                {
                    "asset": asset,
                    "ticker": ticker,
                    "classCode": class_code,
                    "name": name
                }
            )

        result = self.select_nearest(
            instruments
        )

        print()

        print(
            "====== ACTIVE CONTRACTS ======"
        )

        for item in result:

            print(item)

        return result

    # ---------------------------------------------------------
    # CONTRACT DATE
    # ---------------------------------------------------------

    def contract_date(
        self,
        ticker
    ):

        months = {

            "F": 1,
            "G": 2,
            "H": 3,
            "J": 4,
            "K": 5,
            "M": 6,
            "N": 7,
            "Q": 8,
            "U": 9,
            "V": 10,
            "X": 11,
            "Z": 12

        }

        if not ticker:

            return None

        # Обычно тикер содержит код месяца
        # перед последними двумя цифрами года.
        #
        # Например:
        # BMU6
        # GDU6
        # MMU6
        # MTU6

        try:

            month_code = ticker[-2]
            year_code = ticker[-1]

        except IndexError:

            return None

        month = months.get(
            month_code
        )

        if month is None:

            return None

        try:

            year = 2020 + int(
                year_code
            )

        except (
            TypeError,
            ValueError
        ):

            return None

        return (
            year,
            month
        )

    # ---------------------------------------------------------
    # SELECT NEAREST
    # ---------------------------------------------------------

    def select_nearest(
        self,
        instruments
    ):

        if not instruments:

            return []

        result = []

        assets = {
            "BR",
            "GOLD",
            "IMOEX",
            "MX",
            "SI"
        }

        for asset in assets:

            candidates = [
                item
                for item in instruments
                if item.get("asset") == asset
            ]

            if not candidates:

                continue

            candidates_with_date = []

            for item in candidates:

                date = self.contract_date(
                    item.get("ticker")
                )

                if date:

                    candidates_with_date.append(
                        (
                            date,
                            item
                        )
                    )

            if candidates_with_date:

                candidates_with_date.sort(
                    key=lambda x: x[0]
                )

                result.append(
                    candidates_with_date[0][1]
                )

            else:

                result.append(
                    candidates[0]
                )

        return result

    # ---------------------------------------------------------
    # LOAD STOCKS
    # ---------------------------------------------------------

    def load_stocks(self):

        print(
            "📚 Загрузка акций TQBR"
        )

        if not self.api.authorize():

            return []

        stocks = self.api.get_instruments(
            "STOCK"
        )

        if not stocks:

            print(
                "❌ Акции не загружены"
            )

            return []

        result = []

        seen = set()

        for item in stocks:

            ticker = item.get(
                "ticker",
                ""
            )

            if not ticker:

                continue

            if ticker in seen:

                continue

            seen.add(
                ticker
            )

            boards = item.get(
                "boards",
                []
            )

            class_code = "TQBR"

            if boards:

                for board in boards:

                    board_class = board.get(
                        "classCode",
                        ""
                    )

                    if board_class:

                        class_code = board_class

                        if board_class == "TQBR":

                            break

            result.append(
                {
                    "asset": "STOCK",
                    "ticker": ticker,
                    "classCode": class_code,
                    "name": item.get(
                        "shortName",
                        ""
                    ),
                    "displayName": item.get(
                        "displayName",
                        ""
                    ),
                    "lotSize": item.get(
                        "lotSize",
                        1
                    )
                }
            )

        print(
            "Всего акций:",
            len(result)
        )

        return result

    # ---------------------------------------------------------
    # LOAD TRADING UNIVERSE
    # ---------------------------------------------------------

    def load_trading_universe(self):

        print()
        print(
            "📚 Загрузка торгового universe"
        )

        stocks = self.load_stocks()

        futures = self.load()

        benchmark = next(
            (
                item
                for item in futures
                if item.get("asset") == "IMOEX"
                and item.get("ticker") == "IMOEXF"
            ),
            None
        )

        result = list(stocks)

        if benchmark:

            result.append(
                {
                    "asset": "IMOEX",
                    "ticker": benchmark.get(
                        "ticker"
                    ),
                    "classCode": benchmark.get(
                        "classCode",
                        "SPBFUT"
                    ),
                    "name": benchmark.get(
                        "name",
                        "IMOEXF"
                    )
                }
            )

        print()
        print(
            "====== TRADING UNIVERSE ======"
        )

        print(
            "Stocks:",
            len(stocks)
        )

        print(
            "Benchmark:",
            benchmark
        )

        print(
            "Total:",
            len(result)
        )

        return result
