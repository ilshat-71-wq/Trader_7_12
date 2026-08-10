"""
Trader_7_12 Pro

Trade Confirmation Service

Версия 1.1

Назначение:

- финальное подтверждение сделки
- оценка качества сильного торгового setup
- принятие решения EXECUTE / WATCH / EARLY / REJECT
- работа совместно с STRONG_TRADE gate
"""


class TradeConfirmationService:

    def confirm(
        self,
        confidence,
        trade_score,
        rr_ratio,
        breakout_quality,
        volume_ratio,
        momentum_signal,
        trade_allowed,
    ):

        score = 0
        reasons = []

        # ---------------------------------------------------------
        # TRADE FILTER
        # ---------------------------------------------------------

        if not trade_allowed:

            return {
                "confirmation_score": 0,
                "decision": "REJECT",
                "reasons": [
                    "Trade not allowed"
                ],
            }

        score += 10
        reasons.append("Trade allowed")

        # ---------------------------------------------------------
        # CONFIDENCE
        # ---------------------------------------------------------

        if confidence >= 80:

            score += 20
            reasons.append("High confidence")

        elif confidence >= 65:

            score += 10

        # ---------------------------------------------------------
        # TRADE SCORE
        # ---------------------------------------------------------

        if trade_score >= 75:

            score += 20
            reasons.append("Strong trade score")

        elif trade_score >= 65:

            score += 10

        # ---------------------------------------------------------
        # RISK / REWARD
        # ---------------------------------------------------------

        if rr_ratio >= 3:

            score += 15
            reasons.append("RR >= 3")

        elif rr_ratio >= 2:

            score += 10
            reasons.append("RR >= 2")

        # ---------------------------------------------------------
        # BREAKOUT QUALITY
        # ---------------------------------------------------------

        if breakout_quality >= 70:

            score += 15
            reasons.append("Confirmed breakout")

        elif breakout_quality >= 60:

            score += 15
            reasons.append("Strong breakout quality")

        elif breakout_quality >= 40:

            score += 5

        # ---------------------------------------------------------
        # VOLUME
        # ---------------------------------------------------------

        if volume_ratio >= 4:

            score += 10
            reasons.append("Strong volume")

        # ---------------------------------------------------------
        # MOMENTUM
        # ---------------------------------------------------------

        if momentum_signal in (
            "STRONG_LONG",
            "STRONG_SHORT",
        ):

            score += 10
            reasons.append("Strong momentum")

        # ---------------------------------------------------------
        # FINAL DECISION
        # ---------------------------------------------------------

        if score >= 80:

            decision = "EXECUTE"

        elif score >= 65:

            decision = "WATCH"

        elif score >= 50:

            decision = "EARLY"

        else:

            decision = "REJECT"

        return {
            "confirmation_score": score,
            "decision": decision,
            "reasons": reasons,
        }
