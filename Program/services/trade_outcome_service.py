"""
Trader_7_12 Pro

Trade Outcome Service

Версия 0.2

Назначение:

- проверка открытых торговых идей
- определение WIN / LOSS
- расчёт результата
- фиксация времени и причины выхода
"""

from datetime import datetime


class TradeOutcomeService:

    def check_trade(
        self,
        trade,
        current_price
    ):

        signal = trade.get(
            "signal",
            ""
        )

        entry = trade.get(
            "entry"
        )

        stop = trade.get(
            "stop"
        )

        target = trade.get(
            "target"
        )

        if (
            entry is None
            or stop is None
            or target is None
        ):
            return {
                "status": "OPEN",
                "result": None,
                "exit_price": None,
                "profit_points": None,
                "closed_at": None,
                "exit_reason": None,
            }

        result = None
        status = "OPEN"
        exit_price = None
        exit_reason = None

        # ---------------------------------------------------------
        # LONG
        # ---------------------------------------------------------

        if "LONG" in signal:

            if current_price >= target:

                status = "CLOSED"
                result = "WIN"
                exit_price = target
                exit_reason = "TARGET"

            elif current_price <= stop:

                status = "CLOSED"
                result = "LOSS"
                exit_price = stop
                exit_reason = "STOP"

        # ---------------------------------------------------------
        # SHORT
        # ---------------------------------------------------------

        elif "SHORT" in signal:

            if current_price <= target:

                status = "CLOSED"
                result = "WIN"
                exit_price = target
                exit_reason = "TARGET"

            elif current_price >= stop:

                status = "CLOSED"
                result = "LOSS"
                exit_price = stop
                exit_reason = "STOP"

        # ---------------------------------------------------------
        # PROFIT
        # ---------------------------------------------------------

        profit_points = None

        if exit_price is not None:

            if "LONG" in signal:

                profit_points = (
                    exit_price - entry
                )

            elif "SHORT" in signal:

                profit_points = (
                    entry - exit_price
                )

        # ---------------------------------------------------------
        # CLOSE TIME
        # ---------------------------------------------------------

        closed_at = None

        if status == "CLOSED":

            closed_at = datetime.now().isoformat()

        return {

            "status": status,

            "result": result,

            "exit_price": exit_price,

            "profit_points": profit_points,

            "closed_at": closed_at,

            "exit_reason": exit_reason,

        }
