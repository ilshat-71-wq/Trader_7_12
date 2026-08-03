"""
Trader_7_12 Pro

Momentum Service

Версия 0.1

Назначение:
- анализ силы свечи
- расчет импульса
- определение направления движения
- подготовка сигналов для Signal Engine
"""


class MomentumService:


    def __init__(self):

        pass



    # ---------------------------------------------------------

    def analyze(
            self,
            candle,
            average_volume=0
    ):
        """
        Анализ одной свечи

        candle:
        {
            open,
            high,
            low,
            close,
            volume
        }
        """


        open_price = float(
            candle.get(
                "open",
                0
            )
        )


        high = float(
            candle.get(
                "high",
                0
            )
        )


        low = float(
            candle.get(
                "low",
                0
            )
        )


        close = float(
            candle.get(
                "close",
                0
            )
        )


        volume = float(
            candle.get(
                "volume",
                0
            )
        )



        result = {

            "momentum_score": 0,

            "candle_power": 0,

            "range_position": 0,

            "volume_power": 0,

            "signal": "NO_SIGNAL"

        }



        if high <= low:

            return result



        candle_range = high - low



        body = abs(

            close - open_price

        )


        candle_power = (

            body /

            candle_range

        ) * 100



        range_position = (

            (close - low)

            /

            candle_range

        ) * 100



        volume_power = 0



        if average_volume > 0:

            volume_power = (

                volume /

                average_volume

            ) * 100



        momentum_score = 0



        # направление вверх

        if close > open_price:


            momentum_score += candle_power / 2



            if range_position > 70:

                momentum_score += 25



        # направление вниз

        elif close < open_price:


            momentum_score -= candle_power / 2



            if range_position < 30:

                momentum_score -= 25



        if volume_power > 150:

            momentum_score += 20



        elif volume_power < 50:

            momentum_score -= 10



        momentum_score = int(

            max(

                min(

                    momentum_score,

                    100

                ),

                -100

            )

        )



        signal = "NO_SIGNAL"



        if momentum_score >= 70:

            signal = "STRONG_LONG"


        elif momentum_score >= 40:

            signal = "LONG_WATCH"


        elif momentum_score <= -70:

            signal = "STRONG_SHORT"


        elif momentum_score <= -40:

            signal = "SHORT_WATCH"



        result = {

            "momentum_score":

                momentum_score,


            "candle_power":

                round(
                    candle_power,
                    2
                ),


            "range_position":

                round(
                    range_position,
                    2
                ),


            "volume_power":

                round(
                    volume_power,
                    2
                ),


            "signal":

                signal

        }



        return result