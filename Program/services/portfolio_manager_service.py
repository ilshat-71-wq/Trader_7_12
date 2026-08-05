"""
Trader_7_12 Pro

Portfolio Manager Service

Версия 0.1

Назначение:
- выбор лучших независимых торговых идей
- ограничение количества одновременно рекомендуемых сделок
"""


class PortfolioManagerService:

    def select(self, trades, max_positions=3):

        if not trades:
            return []

        trades = sorted(
            trades,
            key=lambda x: (
                x.get("confirmation_score", 0),
                x.get("confidence", 0),
                x.get("trade_score", {}).get("trade_score", 0)
            ),
            reverse=True
        )

        return trades[:max_positions]
