"""
Trader_7_12 Pro

Trade Confirmation Service

Версия 1.0

Назначение:
- финальное подтверждение сделки
- оценка качества сигнала
- принятие решения EXECUTE / WATCH / EARLY / REJECT
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

        # Confidence
        if confidence >= 80:
            score += 20
            reasons.append("High confidence")
        elif confidence >= 65:
            score += 10

        # Trade Score
        if trade_score >= 80:
            score += 20
            reasons.append("Strong trade score")
        elif trade_score >= 65:
            score += 10

        # Risk / Reward
        if rr_ratio >= 3:
            score += 15
            reasons.append("RR >= 3")

        # Breakout
        if breakout_quality >= 70:
            score += 15
            reasons.append("Confirmed breakout")
        elif breakout_quality >= 40:
            score += 5

        # Volume
        if volume_ratio >= 4:
            score += 10
            reasons.append("Strong volume")

        # Momentum
        if momentum_signal in (
            "STRONG_LONG",
            "STRONG_SHORT",
        ):
            score += 10
            reasons.append("Strong momentum")

        # Trade filter
        if trade_allowed:
            score += 10
            reasons.append("Trade allowed")

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