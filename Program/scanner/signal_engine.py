"""
Trader_7_12 Pro

Signal Engine

Версия 0.4

Назначение:
- объединение котировок
- анализ импульса
- анализ объема
- анализ breakout
- итоговый рейтинг сделки
"""


from services.momentum_service import MomentumService



class SignalEngine:


    def __init__(self):

        self.version = "0.4"

        self.signals = []

        self.momentum = MomentumService()



    # ---------------------------------------------------------

    def calculate_score(
            self,
            quote,
            momentum=None,
            money_volume=0,
            rating=0
    ):

        score = 0

        reasons = []


        change = abs(
            float(
                quote.get(
                    "changeRate",
                    0
                )
            )
        )


        bid = quote.get(
            "bid",
            0
        )

        offer = quote.get(
            "offer",
            0
        )

        last = quote.get(
            "last",
            0
        )



        # движение цены

        if change >= 5:

            score += 35

            reasons.append(
                "Strong price movement"
            )


        elif change >= 3:

            score += 25

            reasons.append(
                "Good price movement"
            )


        elif change >= 1:

            score += 15



        # спред

        if bid and offer and last:

            spread = offer - bid

            spread_percent = (

                spread /

                last

            ) * 100



            if spread_percent < 0.2:

                score += 15

                reasons.append(
                    "Tight spread"
                )



        # -----------------------------------
        # Liquidity
        # денежный оборот
        # -----------------------------------

        if money_volume >= 1_000_000_000:

            score += 20

            reasons.append(
                "High liquidity"
            )

        elif money_volume >= 500_000_000:

            score += 15

            reasons.append(
                "Good liquidity"
            )

        elif money_volume >= 100_000_000:

            score += 10


        elif money_volume >= 50_000_000:

            score += 5



        # -----------------------------------
        # Rating quality
        # -----------------------------------

        if rating >= 70:

            score += 10

            reasons.append(
                "High rating"
            )

        elif rating >= 50:

            score += 5



        # momentum

        if momentum:


            m_score = momentum.get(
                "momentum_score",
                0
            )


            if m_score >= 75:

                score += 25

                reasons.append(
                    "Strong momentum"
                )


            elif m_score >= 45:

                score += 15



            elif m_score <= -75:

                score += 25

                reasons.append(
                    "Strong short momentum"
                )



            volume_ratio = momentum.get(
                "volume_ratio",
                0
            )


            if volume_ratio >= 1.5:

                score += 10

                reasons.append(
                    "Volume confirmation"
                )



            if momentum.get(
                "true_breakout",
                False
            ):


                score += 15

                reasons.append(
                    "Breakout confirmed"
                )



        return min(
            score,
            100
        ), reasons



    # ---------------------------------------------------------

    def get_direction(
            self,
            quote,
            momentum=None
    ):


        if momentum:


            signal = momentum.get(
                "signal",
                ""
            )


            if "LONG" in signal:

                return "LONG"



            if "SHORT" in signal:

                return "SHORT"



        change = quote.get(
            "changeRate",
            0
        )


        if change > 0:

            return "LONG"


        if change < 0:

            return "SHORT"


        return "FLAT"



    # ---------------------------------------------------------

    def analyze(
            self,
            quote,
            data=None,
            volume=0,
            money_volume=0,
            rating=0
    ):


        momentum_result = None



        if data:


            if (
                "momentum_score" in data
            ):

                momentum_result = data


            else:

                momentum_result = self.momentum.analyze(
                    data
                )



        score, reasons = self.calculate_score(

            quote,

            momentum_result,

            money_volume,

            rating

        )



        confidence = "LOW"


        if score >= 80:

            confidence = "HIGH"


        elif score >= 60:

            confidence = "MEDIUM"



        return {


            "ticker":

                quote.get(
                    "ticker",
                    ""
                ),


            "price":

                quote.get(
                    "last",
                    0
                ),


            "change":

                quote.get(
                    "changeRate",
                    0
                ),


            "trade_score":

                score,


            "direction":

                self.get_direction(
                    quote,
                    momentum_result
                ),


            "confidence":

                confidence,


            "reasons":

                reasons,


            "momentum":

                momentum_result,


            "status":

                "🔥 TRADE"
                if score >= 75
                else
                "👀 WATCH"
                if score >= 45
                else
                "⛔ SKIP"

        }



    # ---------------------------------------------------------

    def rank(
            self,
            quotes
    ):


        self.signals = []


        for quote in quotes:

            self.signals.append(

                self.analyze(
                    quote
                )

            )



        self.signals.sort(

            key=lambda x:

            x["trade_score"],

            reverse=True

        )


        return self.signals
