"""
Trader_7_12 Pro

Signal Engine

Версия 0.2

Назначение:
- объединение всех торговых факторов
- расчет итоговой уверенности
- классификация сигнала
- объяснение причин
"""


class SignalEngine:


    def analyze(self, analysis):

        volume_score = analysis.get(
            "volume_score",
            0
        )

        momentum_score = analysis.get(
            "momentum_score",
            0
        )

        breakout_score = analysis.get(
            "breakout_score",
            0
        )

        trade_score = analysis.get(
            "trade_score",
            0
        )


        confidence = round(

            trade_score * 0.6
            +
            breakout_score * 0.2
            +
            abs(momentum_score) * 0.2,

            1

        )


        reasons = []


        if volume_score >= 80:

            reasons.append(
                "High volume"
            )


        if momentum_score >= 60:

            reasons.append(
                "Strong momentum"
            )

        elif momentum_score <= -60:

            reasons.append(
                "Strong downside momentum"
            )


        if breakout_score >= 70:

            reasons.append(
                "Breakout confirmed"
            )

        elif breakout_score >= 30:

            reasons.append(
                "Breakout developing"
            )



        signal = "NO_SIGNAL"



        if confidence >= 85:

            if momentum_score >= 0:

                signal = "STRONG_LONG"

            else:

                signal = "STRONG_SHORT"



        elif confidence >= 70:

            if momentum_score >= 0:

                signal = "LONG_WATCH"

            else:

                signal = "SHORT_WATCH"



        elif confidence >= 55:

            if momentum_score >= 0:

                signal = "EARLY_LONG"

            else:

                signal = "EARLY_SHORT"



        return {

            "signal": signal,

            "confidence": confidence,

            "reasons": reasons

        }
