"""
Trader_7_12 Pro

Trade Outcome Service

Версия 0.1

Назначение:
- проверка открытых торговых идей
- определение WIN / LOSS
- расчёт результата
"""


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


        if not entry or not stop or not target:
            return {
                "status": "OPEN",
                "result": None,
            }


        result = None
        status = "OPEN"
        exit_price = None


        # LONG логика

        if "LONG" in signal:

            if current_price >= target:

                status = "CLOSED"
                result = "WIN"
                exit_price = target


            elif current_price <= stop:

                status = "CLOSED"
                result = "LOSS"
                exit_price = stop



        # SHORT логика

        elif "SHORT" in signal:

            if current_price <= target:

                status = "CLOSED"
                result = "WIN"
                exit_price = target


            elif current_price >= stop:

                status = "CLOSED"
                result = "LOSS"
                exit_price = stop



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


        return {

            "status": status,

            "result": result,

            "exit_price": exit_price,

            "profit_points": profit_points,

        }
