"""
Trader_7_12 Pro

Market Loader

Версия 0.6

Назначение:
- подключение к BCS API
- загрузка инструментов рынка
- тест получения котировок
"""


from api.bcs_api import BCSAPI





class MarketLoader:


    def __init__(self):

        self.api = BCSAPI()

        self.data = None



    # ---------------------------------------------------------


    def connect(self):

        return self.api.authorize()



    # ---------------------------------------------------------


    def load(self):

        """
        Загружает инструменты
        и тестирует получение котировок
        """

        print(
            "📊 Загрузка инструментов рынка..."
        )


        if self.api.access_token is None:

            if not self.connect():

                return None



        self.data = self.api.get_instruments(
            "FUTURES"
        )



        if not self.data:

            print(
                "⚠️ Инструменты не получены"
            )

            return None



        print(
            "✅ Инструменты загружены:",
            len(self.data)
        )



        # -------------------------------------------------
        # ТЕСТ QUOTES
        # -------------------------------------------------


        test_instruments = []



        for item in self.data[:3]:


            test_instruments.append(

                {

                    "ticker":
                        item.get(
                            "ticker"
                        ),


                    "classCode":
                        item.get(
                            "primaryBoard"
                        )

                }

            )



        print(
            "\nTEST QUOTE REQUEST:"
        )


        print(
            test_instruments
        )



        quotes = self.api.get_quotes(

            test_instruments

        )



        print(
            "\nTEST QUOTES RESULT:"
        )


        print(
            quotes
        )


        print(
            "\n============================\n"
        )



        return self.data



    # ---------------------------------------------------------


    def load_instruments(
            self,
            instrument_type="FUTURES"
    ):


        return self.api.get_instruments(

            instrument_type

        )