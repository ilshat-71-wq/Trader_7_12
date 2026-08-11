"""
Trader_7_12 Pro

Signal Engine

Версия 0.4

Назначение:

- объединение торговых факторов
- расчет итоговой уверенности
- классификация сигнала
- объяснение причин
- учет Relative Strength относительно IMOEX
- направление сигнала определяется Momentum
- trade_score не создает сигнал самостоятельно
- breakout должен подтверждать направление для сильного сигнала
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
        # SAFE NUMERIC VALUES
        # ---------------------------------------------------------

        try:
            volume_score = float(
                volume_score
            )
        except (TypeError, ValueError):

            volume_score = 0.0

        try:
            momentum_score = float(
                momentum_score
            )
        except (TypeError, ValueError):

            momentum_score = 0.0

        try:
            breakout_score = float(
                breakout_score
            )
        except (TypeError, ValueError):

            breakout_score = 0.0

        try:
            trade_score = float(
                trade_score
            )
        except (TypeError, ValueError):

            trade_score = 0.0

        try:
            breakout_quality_score = float(
                breakout_quality_score
            )
        except (TypeError, ValueError):

            breakout_quality_score = 0.0

        # ---------------------------------------------------------
        # RELATIVE STRENGTH vs IMOEX
        # ---------------------------------------------------------
        #
        # 50 = neutral
        #
        # >= 65 = strong relative strength
        # >= 55 = positive relative strength
        # 45-55 = neutral
        # <= 45 = negative relative strength
        # <= 35 = strong relative weakness
        #
        # RS confirms or conflicts with Momentum direction.
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

        rs_state = "NEUTRAL"

        if relative_strength_score >= 65:

            rs_state = "STRONG"

        elif relative_strength_score >= 55:

            rs_state = "POSITIVE"

        elif relative_strength_score <= 35:

            rs_state = "WEAK"

        elif relative_strength_score <= 45:

            rs_state = "NEGATIVE"

        # ---------------------------------------------------------
        # RS ADJUSTMENT
        # ---------------------------------------------------------

        rs_adjustment = 0.0

        if momentum_score > 0:

            if rs_state == "STRONG":

                rs_adjustment = 10.0

            elif rs_state == "POSITIVE":

                rs_adjustment = 5.0

            elif rs_state == "NEGATIVE":

                rs_adjustment = -5.0

            elif rs_state == "WEAK":

                rs_adjustment = -10.0

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
        # BREAKOUT DIRECTION
        # ---------------------------------------------------------
        #
        # breakout_strength:
        #
        # positive = LONG breakout
        # negative = SHORT breakout
        # zero = no breakout
        #
        # Some callers may provide breakout_direction directly.
        # We support both forms.
        # ---------------------------------------------------------

        breakout_strength = analysis.get(
            "breakout_strength",
            0
        )

        try:

            breakout_strength = float(
                breakout_strength
            )

        except (TypeError, ValueError):

            breakout_strength = 0.0

        breakout_direction = analysis.get(
            "breakout_direction",
            analysis.get(
                "direction",
                ""
            )
        )

        breakout_direction = str(
            breakout_direction
        ).upper()

        # ---------------------------------------------------------
        # BREAKOUT CONFIRMATION
        # ---------------------------------------------------------

        breakout_confirms = False
        breakout_conflicts = False

        if momentum_score > 0:

            if (
                breakout_strength > 0
                or breakout_direction == "LONG"
            ):

                breakout_confirms = (
                    breakout_score > 0
                    or breakout_quality_score > 0
                    or breakout_strength > 0
                )

            elif (
                breakout_strength < 0
                or breakout_direction == "SHORT"
            ):

                breakout_conflicts = True

        elif momentum_score < 0:

            if (
                breakout_strength < 0
                or breakout_direction == "SHORT"
            ):

                breakout_confirms = (
                    breakout_score > 0
                    or breakout_quality_score > 0
                    or breakout_strength < 0
                )

            elif (
                breakout_strength > 0
                or breakout_direction == "LONG"
            ):

                breakout_conflicts = True

        # ---------------------------------------------------------
        # CONFIDENCE
        # ---------------------------------------------------------
        #
        # trade_score = quality/liquidity factor
        # breakout_score = breakout confirmation
        # momentum = directional factor
        # breakout_quality = quality of setup
        # RS = relative strength/weakness adjustment
        #
        # IMPORTANT:
        #
        # trade_score alone cannot create a signal.
        # ---------------------------------------------------------

        confidence = round(

            trade_score * 0.40
            +
            breakout_score * 0.20
            +
            abs(momentum_score) * 0.25
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

        elif volume_score >= 50:

            reasons.append(
                "Good volume"
            )

        # ---------------------------------------------------------
        # MOMENTUM REASONS
        # ---------------------------------------------------------

        if momentum_score >= 60:

            reasons.append(
                "Strong momentum"
            )

        elif momentum_score >= 35:

            reasons.append(
                "Positive momentum"
            )

        elif momentum_score <= -60:

            reasons.append(
                "Strong downside momentum"
            )

        elif momentum_score <= -35:

            reasons.append(
                "Negative momentum"
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
        # BREAKOUT REASONS
        # ---------------------------------------------------------

        if breakout_confirms:

            if breakout_score >= 70:

                reasons.append(
                    "Breakout confirmed"
                )

            elif breakout_score >= 30:

                reasons.append(
                    "Breakout developing"
                )

            else:

                reasons.append(
                    "Breakout supports direction"
                )

        elif breakout_conflicts:

            reasons.append(
                "Breakout conflicts with momentum"
            )

        # ---------------------------------------------------------
        # SIGNAL CLASSIFICATION
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        #
        # No directional momentum = NO_SIGNAL.
        #
        # Therefore a high trade_score with momentum=0
        # cannot generate LONG/SHORT.
        # ---------------------------------------------------------

        signal = "NO_SIGNAL"

        # ---------------------------------------------------------
        # STRONG SIGNAL
        # ---------------------------------------------------------

        if (
            momentum_score >= 50
            and confidence >= 75
            and breakout_quality_score >= 50
            and not breakout_conflicts
        ):

            signal = "STRONG_LONG"

        elif (
            momentum_score <= -50
            and confidence >= 75
            and breakout_quality_score >= 50
            and not breakout_conflicts
        ):

            signal = "STRONG_SHORT"

        # ---------------------------------------------------------
        # WATCH SIGNAL
        # ---------------------------------------------------------

        elif (
            momentum_score >= 35
            and confidence >= 60
            and breakout_quality_score >= 30
            and not breakout_conflicts
        ):

            signal = "LONG_WATCH"

        elif (
            momentum_score <= -35
            and confidence >= 60
            and breakout_quality_score >= 30
            and not breakout_conflicts
        ):

            signal = "SHORT_WATCH"

        # ---------------------------------------------------------
        # EARLY SIGNAL
        # ---------------------------------------------------------
        #
        # Early signal is deliberately weaker.
        #
        # It is a watch candidate, NOT a confirmed trade.
        # ---------------------------------------------------------

        elif (
            momentum_score >= 20
            and confidence >= 50
            and trade_score >= 55
            and not breakout_conflicts
        ):

            signal = "EARLY_LONG"

        elif (
            momentum_score <= -20
            and confidence >= 50
            and trade_score >= 55
            and not breakout_conflicts
        ):

            signal = "EARLY_SHORT"

        # ---------------------------------------------------------
        # NO DIRECTION
        # ---------------------------------------------------------

        if abs(momentum_score) < 20:

            signal = "NO_SIGNAL"

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
            "breakout_strength",
            breakout_strength,
            "RS",
            relative_strength_score,
            "RS state",
            rs_state,
            "RS adjustment",
            rs_adjustment,
            "confidence",
            confidence,
            "signal",
            signal
        )

        # ---------------------------------------------------------
        # RESULT
        # ---------------------------------------------------------

        return {

            "signal":
                signal,

            "confidence":
                confidence,

            "reasons":
                reasons

        }