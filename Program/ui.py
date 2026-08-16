"""
Trader_7_12 Pro

Пользовательский интерфейс

Версия: 0.9

Изменения:
- русские пользовательские подписи
- scanner создаётся лениво только при нажатии «Сканировать рынок»
- при недоступном БКС интерфейс запускается без scanner
- внутренняя торговая логика и ключи данных не изменяются
"""

from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QTextEdit,
)

from PySide6.QtCore import Qt


DIRECTION_LABELS = {
    "LONG": "ЛОНГ",
    "SHORT": "ШОРТ",
}

SETUP_LABELS = {
    "BREAKOUT": "ПРОБОЙ",
    "PULLBACK": "ОТКАТ",
    "REBOUND": "ОТСКОК",
}

SETUP_STATE_LABELS = {
    "READY": "ГОТОВ",
    "WATCH": "НАБЛЮДЕНИЕ",
    "CONFIRMED": "ПОДТВЕРЖДЁН",
}


def label_direction(value):
    return DIRECTION_LABELS.get(value, value or "-")


def label_setup(value):
    return SETUP_LABELS.get(value, value or "-")


def label_setup_state(value):
    return SETUP_STATE_LABELS.get(value, value or "-")


class TraderWindow(QWidget):

    def __init__(self, scanner_enabled=True):
        super().__init__()

        self.setWindowTitle("Trader_7_12 Pro — Утренний радар")
        self.resize(900, 600)

        # ВАЖНО: создание pipeline не выполняется при старте UI.
        # Оно запускается только после нажатия кнопки сканирования.
        self.scanner = None
        self.scanner_enabled = scanner_enabled

        self.init_ui()

    def init_ui(self):
        self.title = QLabel("TRADER_7_12 PRO")
        self.title.setAlignment(Qt.AlignCenter)

        self.subtitle = QLabel("Утренний радар рынка • 07:00–13:00 МСК")
        self.subtitle.setAlignment(Qt.AlignCenter)

        self.scan_button = QPushButton("🔎 Сканировать рынок")
        self.scan_button.clicked.connect(self.run_market_scan)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)

        if not self.scanner_enabled:
            self.scan_button.setEnabled(False)
            self.result_box.setText(
                "👁 РЕЖИМ ПРОСМОТРА\n\n"
                "БКС временно недоступен.\n"
                "Сканирование рынка будет доступно после восстановления подключения."
            )
        else:
            self.result_box.setText(
                "✅ БКС подключён.\n\n"
                "Сканер готов. Нажмите «Сканировать рынок», чтобы запустить анализ."
            )

        layout = QVBoxLayout()
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.result_box)
        self.setLayout(layout)

    def run_market_scan(self):
        if not self.scanner_enabled:
            self.result_box.setText(
                "👁 РЕЖИМ ПРОСМОТРА\n\n"
                "БКС временно недоступен. Сканирование невозможно."
            )
            return

        self.result_box.setText(
            "📡 Сканирование рынка БКС...\n\n"
            "Радар СПОТА → подтверждение ФЬЮЧЕРСА → итоговый кандидат"
        )

        self.scan_button.setEnabled(False)

        try:
            if self.scanner is None:
                from services.morning_trading_pipeline_service import (
                    MorningTradingPipelineService,
                )
                self.scanner = MorningTradingPipelineService()

            results = self.scanner.scan(limit=3)
        except Exception as exc:
            self.result_box.setText(
                "❌ Ошибка сканирования:\n\n"
                f"{exc}"
            )
            self.scan_button.setEnabled(True)
            return

        self.scan_button.setEnabled(True)

        if not results:
            self.result_box.setText(
                "🌙 Готовых кандидатов сейчас нет.\n\n"
                "Радар не нашёл инструменты, прошедшие все проверки."
            )
            return

        output = [
            "================================",
            "TRADER_7_12 PRO",
            "УТРЕННИЙ СПИСОК КАНДИДАТОВ",
            "================================",
            "",
            f"Кандидатов найдено: {len(results)}",
            "",
        ]

        for index, item in enumerate(results, 1):
            output.extend([
                f"#{index}  {item.get('futures_ticker', '-')} / {item.get('spot_ticker', '-')}",
                f"Направление:              {label_direction(item.get('direction'))}",
                f"Вход:                     {item.get('entry', '-')}",
                f"Стоп:                     {item.get('stop_loss', '-')}",
                f"Цель:                     {item.get('take_profit', '-')}",
                f"Соотношение риск/прибыль: {item.get('rr_ratio', '-')}",
                f"Итоговая оценка:          {item.get('candidate_score', '-')}",
                f"Оценка радара:            {item.get('radar_score', '-')}",
                f"Оценка подтверждения:     {item.get('confirmation_score', '-')}",
                f"Относительная сила:       {item.get('relative_strength', '-')}",
                f"Сетап:                    {label_setup(item.get('setup'))}",
                f"Состояние сетапа:         {label_setup_state(item.get('setup_state'))}",
                f"Риск:                     {item.get('actual_risk_amount', '-')}",
                f"Количество:               {item.get('quantity', '-')}",
                "",
                "--------------------------------",
            ])

        output.extend([
            "",
            "ℹ️ РЕЖИМ ТОЛЬКО ДЛЯ АНАЛИЗА — ОРДЕРА НЕ ОТПРАВЛЯЮТСЯ",
            "Логика: РАДАР СПОТА → ПОДТВЕРЖДЕНИЕ ФЬЮЧЕРСА → ИТОГОВЫЙ КАНДИДАТ",
        ])

        self.result_box.setText("\n".join(output))
