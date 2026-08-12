"""
Trader_7_12 Pro

Portfolio Manager Service

Версия 0.2

Назначение:

- ограничение количества одновременно рекомендуемых сделок
- сохранение порядка, определённого TradeRankerService
- безопасная работа с trade_score
- финальный portfolio-level cap
"""


class PortfolioManagerService:

    def select(self, trades, max_positions=3):

        if not trades:
            return []

        if max_positions <= 0:
            return []

        # TradeRankerService уже выполнил основной ranking.
        # Portfolio Manager не должен менять его порядок.
        #
        # Здесь задача только одна:
        # ограничить количество финальных позиций.

        return list(trades[:max_positions])
