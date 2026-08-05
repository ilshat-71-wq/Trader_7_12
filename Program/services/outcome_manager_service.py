"""
Trader_7_12 Pro

Outcome Manager Service

Версия 0.1

Назначение:
- контроль открытых сделок
- проверка достижения stop/target
- обновление торгового журнала
"""


class OutcomeManagerService:


    def __init__(
        self,
        trade_journal_service,
        trade_outcome_service
    ):

        self.trade_journal_service = (
            trade_journal_service
        )

        self.trade_outcome_service = (
            trade_outcome_service
        )



    def evaluate_open_trades(
        self,
        market_prices
    ):

        journal = (
            self.trade_journal_service
            .get_history()
        )


        results = []


        for index, trade in enumerate(journal):


            if trade.get(
                "status"
            ) != "OPEN":

                continue


            ticker = trade.get(
                "ticker"
            )


            current_price = market_prices.get(
                ticker
            )


            if current_price is None:

                continue


            outcome = (
                self.trade_outcome_service
                .check_trade(
                    trade,
                    current_price
                )
            )


            if outcome.get(
                "status"
            ) == "CLOSED":


                updated = (
                    self.trade_journal_service
                    .update_trade(
                        index,
                        outcome
                    )
                )


                results.append(
                    updated
                )


        return results
