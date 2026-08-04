class SignalEngine:

    def __init__(self):

        self.version = "0.2"

        self.signals = []


    # ---------------------------------------------------------

    def calculate_score(self, quote):

        change = abs(
            quote.get(
                "changeRate",
                0
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


        spread = 0


        if bid and offer:

            spread = offer - bid


        score = 0


        # сила движения

        if change >= 5:

            score += 50

        elif change >= 3:

            score += 35

        elif change >= 1:

            score += 20



        # качество спреда

        if spread > 0 and last:

            spread_percent = (
                spread / last
            ) * 100


            if spread_percent < 0.2:

                score += 25

            elif spread_percent < 0.5:

                score += 15



        # волатильность

        if change >= 2:

            score += 10


        return round(
            score,
            1
        )


    # ---------------------------------------------------------

    def get_direction(self, quote):

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

    def get_status(self, score):

        if score >= 70:

            return "🔥 TRADE"


        if score >= 40:

            return "👀 WATCH"


        return "⛔ SKIP"



    # ---------------------------------------------------------

    def analyze(self, quote):

        score = self.calculate_score(
            quote
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

            "spread":
                round(
                    quote.get("offer",0)
                    -
                    quote.get("bid",0),
                    2
                ),

            "score":
                score,

            "direction":
                self.get_direction(
                    quote
                ),

            "status":
                self.get_status(
                    score
                )

        }



    # ---------------------------------------------------------

    def rank(self, quotes):

        self.signals = []


        for quote in quotes:

            signal = self.analyze(
                quote
            )

            self.signals.append(
                signal
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
                f"{s['ticker']:6}",
                f"Цена: {s['price']:10}",
                f"Изм: {s['change']:6.2f}%",
                f"Спред: {s['spread']:6}",
                f"Рейтинг: {s['score']:5}",
                s["direction"]
            )

            print(
                "Статус:",
                s["status"]
            )


# ---------------------------------------------------------