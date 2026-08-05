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

        trade_score_data = analysis.get(
            "trade_score",
            0
        )

        if isinstance(trade_score_data, dict):
            trade_score = trade_score_data.get(
                "trade_score",
                0
            )
        else:
            trade_score = trade_score_data


        breakout_quality_score = analysis.get(
            "breakout_quality_score",
            analysis.get(
                "breakout_quality",
                0
            )
        )


        confidence = round(

            trade_score * 0.5
            +
            breakout_score * 0.15
            +
            abs(momentum_score) * 0.2
            +
            breakout_quality_score * 0.15,

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



        print(
            "DEBUG SIGNAL ENGINE:",
            "volume",
            volume_score,
            "trade",
            trade_score,
            "momentum",
            momentum_score,
            "breakout",
            breakout_score,
            "quality",
            breakout_quality_score,
            "confidence",
            confidence
        )


        signal = "NO_SIGNAL"



        if confidence >= 85 and breakout_quality_score >= 50 and abs(momentum_score) >= 50:

            if momentum_score >= 0:

                signal = "STRONG_LONG"

            else:

                signal = "STRONG_SHORT"



        elif confidence >= 70 and breakout_quality_score >= 35 and abs(momentum_score) >= 35:

            if momentum_score >= 0:

                signal = "LONG_WATCH"

            else:

                signal = "SHORT_WATCH"



        elif (
            confidence >= 50
            and trade_score >= 55
            and breakout_quality_score >= 20
            and abs(momentum_score) >= 20
        ):

            if momentum_score >= 0:

                signal = "EARLY_LONG"

            else:

                signal = "EARLY_SHORT"



        return {

            "signal": signal,

            "confidence": confidence,

            "reasons": reasons

        }
