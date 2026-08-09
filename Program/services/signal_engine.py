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


        # ---------------------------------------------------------
        # RELATIVE STRENGTH vs IMOEX
        # ---------------------------------------------------------

        relative_strength_score = float(
            analysis.get(
                "relative_strength_score",
                50.0
            )
        )

        relative_strength_signal = analysis.get(
            "relative_strength_signal",
            "NEUTRAL"
        )

        # RS confirmation:
        # LONG  + positive RS -> bonus
        # LONG  + negative RS -> penalty
        # SHORT + negative RS -> bonus
        # SHORT + positive RS -> penalty

        rs_adjustment = 0.0

        if momentum_score > 0:

            if relative_strength_signal in (
                "STRONG",
                "POSITIVE"
            ):
                rs_adjustment = 10.0

            elif relative_strength_signal in (
                "WEAK",
                "NEGATIVE"
            ):
                rs_adjustment = -10.0

        elif momentum_score < 0:

            if relative_strength_signal in (
                "WEAK",
                "NEGATIVE"
            ):
                rs_adjustment = 10.0

            elif relative_strength_signal in (
                "STRONG",
                "POSITIVE"
            ):
                rs_adjustment = -10.0


        confidence = round(

            trade_score * 0.5
            +
            breakout_score * 0.15
            +
            abs(momentum_score) * 0.2
            +
            breakout_quality_score * 0.15
              + rs_adjustment,

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


        if relative_strength_signal == "STRONG":
            reasons.append(
                "Relative strength confirms market strength"
            )

        elif relative_strength_signal == "POSITIVE":
            reasons.append(
                "Relative strength supports direction"
            )

        elif relative_strength_signal == "WEAK":
            reasons.append(
                "Relative weakness supports downside"
            )

        elif relative_strength_signal == "NEGATIVE":
            reasons.append(
                "Relative weakness conflicts with long direction"
                if momentum_score > 0
                else
                "Relative weakness supports short direction"
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
