"""
Trader_7_12 Pro

Momentum Service

Версия 0.2

Назначение:
- анализ силы свечи
- расчет импульса
- анализ объема
- оценка денежного оборота
- определение силы пробоя
"""


class MomentumService:


    def __init__(self):

        self.version = "0.2"



    # ---------------------------------------------------------

    def analyze(
            self,
            candle,
            average_volume=0,
            average_money_volume=0
    ):


        open_price = float(
            candle.get("open", 0)
        )

        high = float(
            candle.get("high", 0)
        )

        low = float(
            candle.get("low", 0)
        )

        close = float(
            candle.get("close", 0)
        )

        volume = float(
            candle.get("volume", 0)
        )

        money_volume = float(
            candle.get(
                "money_volume",
                0
            )
        )



        result = {

            "momentum_score": 0,

            "candle_power": 0,

            "range_position": 0,

            "volume_ratio": 0,

            "money_volume_ratio": 0,

            "breakout_strength": 0,

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



        volume_ratio = 0


        if average_volume > 0:

            volume_ratio = (

                volume /

                average_volume

            )



        money_volume_ratio = 0


        if average_money_volume > 0:

            money_volume_ratio = (

                money_volume /

                average_money_volume

            )



        breakout_strength = 0



        if close >= high * 0.995:

            breakout_strength = 100


        elif close >= high * 0.98:

            breakout_strength = 70



        elif close <= low * 1.005:

            breakout_strength = -100



        momentum_score = 0



        # направление свечи

        if close > open_price:


            momentum_score += candle_power / 2


            if range_position > 70:

                momentum_score += 20



        elif close < open_price:


            momentum_score -= candle_power / 2


            if range_position < 30:

                momentum_score -= 20



        # объем

        if volume_ratio >= 2:

            momentum_score += 25


        elif volume_ratio >= 1.5:

            momentum_score += 15


        elif volume_ratio < 0.7:

            momentum_score -= 10



        # денежный объем

        if money_volume_ratio >= 2:

            momentum_score += 15



        # пробой

        if breakout_strength == 100:

            momentum_score += 20


        elif breakout_strength == -100:

            momentum_score -= 20



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



        if momentum_score >= 75:

            signal = "STRONG_LONG"


        elif momentum_score >= 45:

            signal = "LONG_WATCH"


        elif momentum_score <= -75:

            signal = "STRONG_SHORT"


        elif momentum_score <= -45:

            signal = "SHORT_WATCH"



        return {


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


            "volume_ratio":

                round(
                    volume_ratio,
                    2
                ),


            "money_volume_ratio":

                round(
                    money_volume_ratio,
                    2
                ),


            "breakout_strength":

                breakout_strength,


            "signal":

                signal

        }
