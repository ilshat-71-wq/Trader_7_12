"""
Trader_7_12 Pro

Market Data

Версия 0.5

Назначение:
- получение инструментов BCS
- получение котировок BCS
- получение последних сделок BCS
- расчёт денежного оборота
- подготовка данных для сканера
"""


from market.market_loader import MarketLoader



class MarketData:


    def __init__(self):

        self.loader = MarketLoader()

        self.instruments = []



    # ---------------------------------------------------------

    def connect(self):

        return self.loader.connect()



    # ---------------------------------------------------------

    def update(self):


        print(
            "\n📡 Запрос данных рынка..."
        )


        instruments = self.loader.load()



        if not instruments:

            print(
                "⚠️ Инструменты отсутствуют"
            )

            return []



        print(
            "Получено инструментов:",
            len(instruments)
        )



        # =============================================
        # QUOTES
        # =============================================


        quote_request = []


        for item in instruments:


            quote_request.append(

                {

                    "ticker":
                        item.get("ticker"),


                    "classCode":
                        item.get("primaryBoard")

                }

            )



        all_quotes = []


        batch_size = 100



        for i in range(
            0,
            len(quote_request),
            batch_size
        ):


            batch = quote_request[
                i:i + batch_size
            ]


            print(
                f"📊 Quotes batch {i//batch_size + 1}:",
                len(batch)
            )


            response = self.loader.api.get_quotes(
                batch
            )



            if isinstance(
                response,
                dict
            ):


                records = response.get(
                    "records",
                    []
                )


                all_quotes.extend(
                    records
                )



        print(
            "Всего котировок получено:",
            len(all_quotes)
        )



        quotes_map = {}



        for quote in all_quotes:


            key = (

                quote.get("ticker"),

                quote.get("classCode")

            )


            quotes_map[key] = quote




        # =============================================
        # FILTER ACTIVE
        # =============================================


        active = []


        for item in instruments:


            key = (

                item.get("ticker"),

                item.get("primaryBoard")

            )


            quote = quotes_map.get(
                key
            )


            if quote:


                active.append(
                    item
                )



        print(
            "Активных инструментов:",
            len(active)
        )



        # =============================================
        # TRADES
        # =============================================


        print(
            "\n📈 Расчёт объёмов сделок..."
        )


        trades_map = {}



        # пока первые 50 для проверки API


        for item in active[:50]:


            ticker = item.get(
                "ticker"
            )


            class_code = item.get(
                "primaryBoard"
            )



            trades = self.loader.api.get_last_trades(

                ticker,

                class_code

            )


            if ticker == active[0].get("ticker"):


                print()

                print(
                    "========== RAW FIRST TRADE =========="
                )


                records = trades.get(
                    "records",
                    []
                )


                if records:

                    print(
                        records[0]
                    )

                else:

                    print(
                        "Нет сделок"
                    )


                print(
                    "===================================="
                )

                print()



            money_volume = 0



            records = trades.get(
                "records",
                []
            )



            for trade in records:



                price = (

                    trade.get("price")

                    or

                    trade.get("last")

                    or

                    trade.get("tradePrice")

                    or

                    0

                )



                quantity = (

                    trade.get("quantity")

                    or

                    trade.get("volume")

                    or

                    trade.get("amount")

                    or

                    0

                )



                try:


                    money_volume += (

                        float(price)

                        *

                        float(quantity)

                    )


                except:


                    pass



            trades_map[

                (

                ticker,

                class_code

                )

            ] = money_volume



            print(
                f"Trades {ticker}: {len(records)}"
            )



        print(
            "Объёмы рассчитаны:",
            len(trades_map)
        )



        # =============================================
        # SCANNER DATA
        # =============================================


        result = []



        for item in active:


            key = (

                item.get("ticker"),

                item.get("primaryBoard")

            )


            quote = quotes_map.get(
                key,
                {}
            )



            money_volume = trades_map.get(
                key,
                0
            )



            result.append(

                {

                    "ticker":

                        item.get(
                            "ticker"
                        ),


                    "price":

                        quote.get(
                            "last",
                            0
                        ),


                    "volume":

                        money_volume,


                    "money_volume":

                        money_volume,


                    "average_volume":

                        1,


                    "classCode":

                        item.get(
                            "primaryBoard"
                        )

                }

            )



        result.sort(

            key=lambda x:
                x["money_volume"],

            reverse=True

        )



        self.instruments = result



        print(
            "\n🔥 ТОП ликвидности:"
        )



        for row in result[:10]:


            print(

                row["ticker"],

                "Цена:",

                row["price"],

                "Оборот:",

                row["money_volume"]

            )



        return result