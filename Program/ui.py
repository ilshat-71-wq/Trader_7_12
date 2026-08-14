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



from services.morning_trading_pipeline_service import MorningTradingPipelineService




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




        self.scanner = MorningTradingPipelineService()


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
            "📡 Сканирование рынка BCS...\\n\\n"
            "SPOT Radar → Futures Confirmation → Final Trade"
        )

        try:
            results = self.scanner.scan(limit=3)
        except Exception as exc:
            self.result_box.setText(
                "❌ Ошибка сканирования:\\n\\n"
                f"{exc}"
            )
            return

        if not results:
            self.result_box.setText(
                "🌙 Готовых торговых идей сейчас нет.\\n\\n"
                "Pipeline не нашёл кандидатов, прошедших все проверки."
            )
            return

        output = [
            "================================",
            "TRADER_7_12 PRO",
            "MORNING TRADE SHORTLIST",
            "================================",
            "",
            f"Готовых сделок: {len(results)}",
            "",
        ]

        for index, item in enumerate(results, 1):
            output.extend([
                f"#{index}  {item.get('futures_ticker', '-')}"
                f" / {item.get('spot_ticker', '-')}",
                f"Направление: {item.get('direction', '-')}",
                f"Вход:        {item.get('entry', '-')}",
                f"Стоп:        {item.get('stop_loss', '-')}",
                f"Цель:        {item.get('take_profit', '-')}",
                f"RR:          {item.get('rr_ratio', '-')}",
                f"Score:       {item.get('candidate_score', '-')}",
                f"Radar:       {item.get('radar_score', '-')}",
                f"Confirmation:{item.get('confirmation_score', '-')}",
                f"RS:          {item.get('relative_strength', '-')}",
                f"Setup:       {item.get('setup', '-')}",
                f"Setup state: {item.get('setup_state', '-')}",
                f"Risk:        {item.get('actual_risk_amount', '-')}",
                f"Quantity:    {item.get('quantity', '-')}",
                "",
                "--------------------------------",
            ])

        output.extend([
            "",
            "READ ONLY — ОРДЕРА НЕ ОТПРАВЛЯЮТСЯ",
            "Pipeline: SPOT RADAR → FUTURES CONFIRMATION → FINAL TRADE",
        ])

        self.result_box.setText("\n".join(output))
