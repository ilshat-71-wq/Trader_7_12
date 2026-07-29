from scanner.instrument_loader import InstrumentLoader
from scanner.signal_engine import SignalEngine

from api.bcs_api import BCSAPI



class MarketScanner:


    def __init__(self):

        self.loader = InstrumentLoader()

        self.api = BCSAPI()

        self.engine = SignalEngine()



    # ---------------------------------------------------------

    def get_active_futures(self):

        return self.loader.get_active_contracts()



    # ---------------------------------------------------------

    def run(self):

        print(
            "🚀 Market Scanner v0.4"
        )


        print(
            "📚 Загрузка ближайших фьючерсов"
        )


        contracts = self.get_active_futures()



        if not contracts:

            print(
                "❌ Фьючерсы не найдены"
            )

            return



        print()

        print(
            "Активных контрактов:",
            len(contracts)
        )



        if not self.api.authorize():

            return



        instruments = []



        for c in contracts:

            instruments.append(

                {

                    "ticker":
                        c["ticker"],

                    "classCode":
                        c["classCode"]

                }

            )



        quotes = self.api.get_quotes(
            instruments
        )



        records = quotes.get(
            "records",
            []
        )



        if not records:

            print(
                "❌ Нет котировок"
            )

            return



        print()

        print(
            "====== TRADER_7_12 SIGNALS ======"
        )



        signals = self.engine.rank(
            records
        )



        if not signals:

            print(
                "Нет сигналов"
            )

            return



        for i, s in enumerate(
            signals,
            start=1
        ):


            emoji = "🔥"


            if s["score"] < 30:

                emoji = "▫️"



            print()

            print(
                f"{emoji} #{i} {s['ticker']}"
            )


            print(
                f"Цена: {s['price']}"
            )


            print(
                f"Изменение: {s['change']:.2f}%"
            )


            print(
                f"Спред: {s['spread']}"
            )


            print(
                f"Score: {s['score']}"
            )


            print(
                f"Направление: {s['direction']}"
            )



# -------------------------------------------------------------


if __name__ == "__main__":


    scanner = MarketScanner()


    scanner.run()