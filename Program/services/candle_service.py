"""
Trader_7_12 Pro

Candle Service

Версия 0.1

Назначение:
- построение свечей из last-trades BCS
- агрегация сделок
- подготовка данных для momentum engine
"""


from datetime import datetime, timezone


class CandleService:


    def __init__(self):

        pass



    # ---------------------------------------------------------

    def build_candles(
            self,
            trades,
            timeframe_minutes=5
    ):
        """
        Построение свечей

        trades:
        [
            {
                price: float,
                volume: float,
                time: str
            }
        ]

        timeframe_minutes:
            5
            15
        """


        if not trades:

            return []



        candles = {}



        for trade in trades:


            price = float(

                trade.get(
                    "price",
                    0
                )

            )


            volume = float(

                trade.get(
                    "volume",
                    trade.get(
                        "quantity",
                        0
                    )
                )

            )


            time_value = trade.get(
                "time"
            )


            if not time_value:

                continue



            try:

                dt = datetime.fromisoformat(

                    time_value.replace(
                        "Z",
                        "+00:00"
                    )

                )


            except Exception:

                continue



            minute = (

                dt.minute //

                timeframe_minutes

            ) * timeframe_minutes



            candle_time = dt.replace(

                minute=minute,

                second=0,

                microsecond=0

            )



            key = candle_time.isoformat()



            if key not in candles:


                candles[key] = {


                    "time":

                        key,


                    "open":

                        price,


                    "high":

                        price,


                    "low":

                        price,


                    "close":

                        price,


                    "volume":

                        0,


                    "money_volume":

                        0


                }



            candle = candles[key]



            candle["high"] = max(

                candle["high"],

                price

            )


            candle["low"] = min(

                candle["low"],

                price

            )


            candle["close"] = price



            candle["volume"] += volume



            candle["money_volume"] += (

                volume *

                price

            )



        result = list(

            candles.values()

        )



        result.sort(

            key=lambda x:

            x["time"]

        )



        return result