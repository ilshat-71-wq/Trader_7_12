"""
Trader_7_12 Pro

Signal Engine

Версия 0.3

Назначение:

- объединение торговых факторов
- расчет итоговой уверенности
- классификация сигнала
- объяснение причин
- учет Relative Strength относительно IMOEX
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
        #
        # Используем числовой RS score.
        #
        # 50 = нейтрально
        #
        # >= 65  = сильная относительная сила
        # >= 55  = положительная относительная сила
        # 45-55  = нейтрально
        # <= 45  = отрицательная относительная сила
        # <= 35  = сильная относительная слабость
        #
        # Это позволяет RS реально участвовать в Signal Engine,
        # даже если текстовый RS signal пока NEUTRAL.
        # ---------------------------------------------------------

        try:
            relative_strength_score = float(
                analysis.get(
                    "relative_strength_score",
                    50.0
                )
            )
        except (TypeError, ValueError):
            relative_strength_score = 50.0

        rs_adjustment = 0.0

        rs_state = "NEUTRAL"

        if relative_strength_score >= 65:

            rs_state = "STRONG"

        elif relative_strength_score >= 55:

            rs_state = "POSITIVE"

        elif relative_strength_score <= 35:

            rs_state = "WEAK"

        elif relative_strength_score <= 45:

            rs_state = "NEGATIVE"

        # LONG confirmation
        if momentum_score > 0:

            if rs_state == "STRONG":
                rs_adjustment = 10.0

            elif rs_state == "POSITIVE":
                rs_adjustment = 5.0

            elif rs_state == "NEGATIVE":
                rs_adjustment = -5.0

            elif rs_state == "WEAK":
                rs_adjustment = -10.0

        # SHORT confirmation
        elif momentum_score < 0:

            if rs_state == "WEAK":
                rs_adjustment = 10.0

            elif rs_state == "NEGATIVE":
                rs_adjustment = 5.0

            elif rs_state == "POSITIVE":
                rs_adjustment = -5.0

            elif rs_state == "STRONG":
                rs_adjustment = -10.0

        # ---------------------------------------------------------
        # CONFIDENCE
        # ---------------------------------------------------------

        confidence = round(

            trade_score * 0.5
            +
            breakout_score * 0.15
            +
            abs(momentum_score) * 0.2
            +
            breakout_quality_score * 0.15
            +
            rs_adjustment,

            1
        )

        confidence = max(
            0.0,
            min(
                100.0,
                confidence
            )
        )

        # ---------------------------------------------------------
        # REASONS
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # RS REASONS
        # ---------------------------------------------------------

        if momentum_score > 0:

            if rs_state == "STRONG":

                reasons.append(
                    "Strong relative strength confirms long"
                )

            elif rs_state == "POSITIVE":

                reasons.append(
                    "Relative strength supports long"
                )

            elif rs_state == "NEGATIVE":

                reasons.append(
                    "Relative weakness conflicts with long"
                )

            elif rs_state == "WEAK":

                reasons.append(
                    "Strong relative weakness conflicts with long"
                )

        elif momentum_score < 0:

            if rs_state == "WEAK":

                reasons.append(
                    "Strong relative weakness confirms short"
                )

            elif rs_state == "NEGATIVE":

                reasons.append(
                    "Relative weakness supports short"
                )

            elif rs_state == "POSITIVE":

                reasons.append(
                    "Relative strength conflicts with short"
                )

            elif rs_state == "STRONG":

                reasons.append(
                    "Strong relative strength conflicts with short"
                )

        # ---------------------------------------------------------
        # BREAKOUT
        # ---------------------------------------------------------

        if breakout_score >= 70:

            reasons.append(
                "Breakout confirmed"
            )

        elif breakout_score >= 30:

            reasons.append(
                "Breakout developing"
            )

        # ---------------------------------------------------------
        # DEBUG
        # ---------------------------------------------------------

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
            "RS",
            relative_strength_score,
            "RS state",
            rs_state,
            "RS adjustment",
            rs_adjustment,
            "confidence",
            confidence
        )

        # ---------------------------------------------------------
        # SIGNAL CLASSIFICATION
        # ---------------------------------------------------------

        signal = "NO_SIGNAL"

        if (
            confidence >= 85
            and breakout_quality_score >= 50
            and abs(momentum_score) >= 50
        ):

            if momentum_score >= 0:

                signal = "STRONG_LONG"

            else:

                signal = "STRONG_SHORT"

        elif (
            confidence >= 70
            and breakout_quality_score >= 35
            and abs(momentum_score) >= 35
        ):

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
