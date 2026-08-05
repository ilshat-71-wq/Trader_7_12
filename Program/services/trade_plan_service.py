"""
Trader_7_12 Pro

Trade Plan Service

Версия 0.1

Назначение:
- расчет торгового плана
- определение входа
- расчет стопа
- расчет цели
- расчет риск/прибыль
"""


class TradePlanService:


    def generate_plan(
        self,
        current_price,
        signal,
        momentum_score,
        breakout_score
    ):

        if signal in (
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        ):

            direction = "SHORT"

            entry = current_price

            stop_loss = round(
                current_price * 1.005,
                2
            )

            take_profit = round(
                current_price * 0.985,
                2
            )


        elif signal in (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG"
        ):

            direction = "LONG"

            entry = current_price

            stop_loss = round(
                current_price * 0.995,
                2
            )

            take_profit = round(
                current_price * 1.015,
                2
            )


        else:

            return {

                "trade_plan": False,

                "reason": "No active signal"

            }


        risk = abs(
            entry - stop_loss
        )

        reward = abs(
            take_profit - entry
        )


        rr_ratio = round(

            reward / risk,

            2

        ) if risk else 0


        return {

            "trade_plan": True,

            "direction": direction,

            "entry": entry,

            "stop_loss": stop_loss,

            "take_profit": take_profit,

            "rr_ratio": rr_ratio,

            "momentum_score": momentum_score,

            "breakout_score": breakout_score

        }
