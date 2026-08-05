"""
Trader_7_12 Pro

Diagnostic Service

Версия 0.2

Назначение:
- прозрачность торгового рейтинга
- анализ компонентов score
- вывод финального торгового решения
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
            "Momentum signal:",
            item.get("momentum_signal", "N/A")
        )


        print(
            "Breakout score:",
            item.get("breakout_score", 0)
        )


        print(
            "Breakout quality:",
            item.get("breakout_quality_score", 0)
        )


        print(
        )


        print(
            "Trade score:",
            item.get("trade_score")
        )


        print()

        print("🚦 FINAL SIGNAL")


        print(
            "Signal:",
            item.get("final_signal", "NO_SIGNAL")
        )


        print(
            "Confidence:",
            item.get("confidence")
        )


        reasons = item.get(
            "reasons",
            []
        )


        if reasons:

            print(
                "Reasons:"
            )

            for reason in reasons:

                print(
                    "-",
                    reason
                )
