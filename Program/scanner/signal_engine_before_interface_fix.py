"""
Trader_7_12 Pro

Signal Engine

Версия 0.3

Назначение:
- объединение котировок
- анализ импульса
- оценка объема
- расчет итогового рейтинга
- подготовка сигналов LONG/SHORT
"""


from services.momentum_service import MomentumService



class SignalEngine:


    def __init__(self):

        self.version = "0.3"

        self.signals = []

        self.momentum = MomentumService()



    # ---------------------------------------------------------

    def calculate_score(
            self,
            quote,
            momentum=None
    ):

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
            1
        )


        score = 0



        # движение цены

        if change >= 5:

            score += 40

        elif change >= 3:

            score += 30

        elif change >= 1:

            score += 15



        # спред

        if bid and offer and last:

            spread = offer - bid

            spread_percent = (
                spread / last
            ) * 100


            if spread_percent < 0.2:

                score += 20

            elif spread_percent < 0.5:

                score += 10



        # импульс свечи

        if momentum:

            m_score = momentum.get(
                "momentum_score",
                0
            )


            if m_score >= 70:

                score += 30


            elif m_score >= 40:

                score += 15


            elif m_score <= -70:

                score += 30


            elif m_score <= -40:

                score += 15



        return round(
            min(score,100),
            1
        )



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

    def get_status(
            self,
            score
    ):

        if score >= 75:

            return "🔥 TRADE"


        if score >= 45:

            return "👀 WATCH"


        return "⛔ SKIP"



    # ---------------------------------------------------------

    def analyze(
            self,
            quote,
            candle=None
    ):


        momentum_result = None


        if candle:


            momentum_result = self.momentum.analyze(

                candle

            )



        score = self.calculate_score(

            quote,

            momentum_result

        )



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



            "score":

                score,



            "direction":

                self.get_direction(

                    quote,

                    momentum_result

                ),



            "momentum":

                momentum_result,



            "status":

                self.get_status(

                    score

                )

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

            x["score"],

            reverse=True

        )


        return self.signals



    # ---------------------------------------------------------

    def print_report(self):


        print()

        print(
            "====== SIGNAL ENGINE ======"
        )


        for s in self.signals:


            print()

            print(

                f"{s['ticker']:8}",

                f"Цена:{s['price']}",

                f"Изм:{s['change']}%",

                f"Рейтинг:{s['score']}",

                s["direction"]

            )


            print(

                "Статус:",

                s["status"]

            )
