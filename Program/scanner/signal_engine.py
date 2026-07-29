class SignalEngine:


    def __init__(self):

        self.results = []



    # ---------------------------------------------------------

    def calculate_signal(
        self,
        quote
    ):


        ticker = quote.get(
            "ticker",
            ""
        )


        price = quote.get(
            "last",
            0
        )


        change = quote.get(
            "changeRate",
            0
        )


        bid = quote.get(
            "bid",
            0
        )


        offer = quote.get(
            "offer",
            0
        )



        # защита от ошибок

        if not price:

            return None



        # -------------------------------------------------
        # Спред

        spread = 0


        if bid and offer:

            spread = offer - bid



        # -------------------------------------------------
        # Базовая сила движения

        movement_score = abs(change) * 10



        # -------------------------------------------------
        # Оценка спреда

        spread_score = 0


        if price:

            spread_percent = (
                spread / price * 100
            )


            if spread_percent < 0.05:

                spread_score = 20


            elif spread_percent < 0.15:

                spread_score = 10



        # -------------------------------------------------
        # Итоговый рейтинг

        score = (

            movement_score

            +

            spread_score

        )


        if score > 100:

            score = 100



        # направление

        direction = "UP"


        if change < 0:

            direction = "DOWN"



        return {

            "ticker": ticker,

            "price": price,

            "change": change,

            "spread": round(
                spread,
                2
            ),

            "score": round(
                score,
                1
            ),

            "direction": direction

        }



    # ---------------------------------------------------------

    def rank(
        self,
        quotes
    ):


        self.results = []



        for q in quotes:


            signal = self.calculate_signal(
                q
            )


            if signal:

                self.results.append(
                    signal
                )



        self.results.sort(

            key=lambda x:
                x["score"],

            reverse=True

        )


        return self.results



    # ---------------------------------------------------------

    def print_report(
        self
    ):


        print()

        print(
            "====== SIGNAL ENGINE ======"
        )


        for item in self.results:


            print(

                f"{item['ticker']:8}"

                f" Цена: {item['price']:10}"

                f" Изм: {item['change']:6.2f}%"

                f" Спред: {item['spread']:6}"

                f" Рейтинг: {item['score']:5}"

                f" {item['direction']}"

            )