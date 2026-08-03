"""
Trader_7_12 Pro

Candle Service

Версия 0.3

Назначение:
- построение свечей из BCS trades
- агрегация сделок
- подготовка данных для momentum engine
"""


from datetime import datetime


class CandleService:


    def __init__(self):

        pass



    # ---------------------------------------------------------

    def build_candles(
            self,
            trades,
            timeframe_minutes=5
    ):


        if not trades:

            return []



        candles = {}



        for trade in trades:


            try:

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
                    "time",
                    trade.get(
                        "dateTime"
                    )
                )


                if not time_value:

                    continue



                dt = datetime.fromisoformat(

                    time_value.replace(
                        "Z",
                        "+00:00"
                    )

                )


            except Exception:

                continue



            if price <= 0:

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

                        0,


                    "trade_count":

                        0,


                    "price_sum":

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

                price *

                volume

            )


            candle["trade_count"] += 1


            candle["price_sum"] += price



        result = []



        for candle in candles.values():


            candle["average_price"] = round(

                candle["price_sum"] /

                candle["trade_count"],

                4

            )


            del candle["price_sum"]


            result.append(candle)



        result.sort(

            key=lambda x:

            x["time"]

        )


        return result
