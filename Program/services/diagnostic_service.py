"""
Trader_7_12 Pro

Diagnostic Service

Версия 0.1

Назначение:
- вывод прозрачности торгового рейтинга
- анализ компонентов score
"""


class DiagnosticService:


    def print_analysis(self, item):

        print()

        print("🔎 DIAGNOSTIC")

        print(
            "Ticker:",
            item.get("ticker")
        )

        print(
            "Money volume:",
            round(
                item.get("money_volume_real", 0),
                2
            )
        )

        print(
            "Volume score:",
            item.get("volume_score")
        )

        print(
            "Volume ratio:",
            item.get("volume_ratio")
        )

        print(
            "Money ratio:",
            item.get("money_ratio")
        )

        print(
            "Momentum:",
            item.get("momentum_score")
        )

        print(
            "Signal:",
            item.get("signal")
        )

        print(
            "Trade score:",
            item.get("trade_score")
        )
