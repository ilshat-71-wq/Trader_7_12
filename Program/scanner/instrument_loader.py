from api.bcs_api import BCSAPI


class InstrumentLoader:

    def __init__(self):

        self.api = BCSAPI()


    # ---------------------------------------------------------

    def get_active_contracts(self):

        return self.load()



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


            if "BR" in text:

                asset = "BR"


            elif "MTSI" in text or ticker.startswith("SI"):

                asset = "SI"


            elif "GOLD" in text:

                asset = "GOLD"


            elif "MX" in text:

                asset = "MX"



            if asset:


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

    def contract_date(self, ticker):

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


        if len(ticker) < 2:

            return 999999


        month_code = ticker[-2]

        year_code = ticker[-1]


        month = months.get(
            month_code,
            12
        )


        year = 2020 + int(
            year_code
        )


        return (

            year * 100
            +
            month

        )



    # ---------------------------------------------------------

    def select_nearest(self, instruments):


        selected = {}


        for item in instruments:


            asset = item["asset"]


            if asset not in selected:

                selected[asset] = item


            else:

                old = selected[asset]


                if self.contract_date(
                    item["ticker"]
                ) < self.contract_date(
                    old["ticker"]
                ):

                    selected[asset] = item



        return list(
            selected.values()
        )



# ---------------------------------------------------------


if __name__ == "__main__":


    loader = InstrumentLoader()


    data = loader.get_active_contracts()


    print()

    print(
        "Всего активных:",
        len(data)
    )