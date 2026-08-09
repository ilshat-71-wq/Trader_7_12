"""
Trader_7_12 Pro

UI Module

Версия:
0.6

Изменения:
- подключен MarketData
- получение реальных данных BCS API
- кнопка "Сканировать рынок"
- расчёт вынесен из UI
"""


from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QTextEdit
)

from PySide6.QtCore import Qt



from scanner.volume_scanner import VolumeScanner




class TraderWindow(QWidget):


    def __init__(self):

        super().__init__()


        self.setWindowTitle(
            "Trader_7_12 Pro"
        )


        self.resize(
            900,
            600
        )




        self.scanner = VolumeScanner()


        self.init_ui()



    def init_ui(self):


        self.title = QLabel(
            "TRADER_7_12 PRO"
        )


        self.title.setAlignment(
            Qt.AlignCenter
        )



        self.scan_button = QPushButton(
            "Сканировать рынок"
        )


        self.scan_button.clicked.connect(
            self.run_market_scan
        )



        self.result_box = QTextEdit()


        self.result_box.setReadOnly(
            True
        )



        layout = QVBoxLayout()


        layout.addWidget(
            self.title
        )


        layout.addWidget(
            self.scan_button
        )


        layout.addWidget(
            self.result_box
        )


        self.setLayout(
            layout
        )




    def run_market_scan(self):
        self.result_box.setText(
            "📡 Сканирование рынка BCS...\n\n"
            "VolumeScanner анализирует ликвидность, объём, momentum и breakout."
        )

        try:
            results = self.scanner.scan()
        except Exception as exc:
            self.result_box.setText(
                "❌ Ошибка сканирования:\n\n"
                f"{exc}"
            )
            return

        if not results:
            self.result_box.setText(
                "⚠️ Торговые данные отсутствуют."
            )
            return

        # Показываем только реальные торговые идеи.
        tradable = [
            item for item in results
            if item.get("signal") not in ("NO_SIGNAL", None)
        ]

        if not tradable:
            self.result_box.setText(
                "🌙 Активных торговых идей нет.\n\n"
                "Scanner завершил анализ без сигнала."
            )
            return

        tradable.sort(
            key=lambda item: float(item.get("confidence", 0)),
            reverse=True
        )

        output = [
            "================================",
            "TRADER_7_12 PRO",
            "TOP TRADE IDEAS",
            "================================",
            "",
            f"Всего результатов: {len(results)}",
            f"Торговых идей: {len(tradable)}",
            ""
        ]

        for index, item in enumerate(tradable[:3], start=1):
            ticker = item.get("ticker", "UNKNOWN")
            signal = item.get(
                "final_signal",
                item.get("signal", "NO_SIGNAL")
            )

            confidence = item.get("confidence", 0)
            trade_score = item.get("trade_score", {})
            trade_score_value = (
                trade_score.get("trade_score", 0)
                if isinstance(trade_score, dict)
                else trade_score
            )

            entry = item.get("entry")
            stop = item.get("stop_loss", item.get("stop"))
            target = item.get("target")

            rr = item.get("rr_ratio", 0)

            volume_score = item.get("volume_score", 0)
            volume_ratio = item.get("volume_ratio", 0)
            momentum = item.get("momentum_score", 0)
            breakout = item.get("breakout_score", 0)

            confirmation = item.get(
                "confirmation_decision",
                "UNKNOWN"
            )

            output.extend([
                "",
                f"#{index}  {ticker}",
                "--------------------------------",
                f"Signal:       {signal}",
                f"Confidence:   {confidence}",
                f"Trade score:  {trade_score_value}",
                f"Confirmation: {confirmation}",
                "",
                f"Entry:        {entry}",
                f"Stop:         {stop}",
                f"Target:       {target}",
                f"RR:           {rr}",
                "",
                f"Volume score: {volume_score}",
                f"Volume ratio: {volume_ratio}",
                f"Momentum:     {momentum}",
                f"Breakout:     {breakout}",
            ])

            reasons = item.get("reasons", [])

            if reasons:
                output.extend([
                    "",
                    "Reasons:"
                ])

                for reason in reasons:
                    output.append(f"- {reason}")

            trade_idea = item.get("trade_idea")

            if trade_idea:
                output.extend([
                    "",
                    f"Idea: {trade_idea}"
                ])

            output.append("")

        self.result_box.setText("\n".join(output))



if __name__ == "__main__":


    app = QApplication([])


    window = TraderWindow()


    window.show()


    app.exec()