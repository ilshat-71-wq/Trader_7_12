"""Trader_7_12 Pro — professional morning radar UI."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


DIRECTION_LABELS = {
    "LONG": "ЛОНГ",
    "SHORT": "ШОРТ",
}

SETUP_LABELS = {
    "BREAKOUT": "ПРОБОЙ",
    "PULLBACK": "ОТКАТ",
    "REBOUND": "ОТСКОК",
    "FIRST_PULLBACK": "ПЕРВЫЙ ОТКАТ",
    "FIRST_REBOUND": "ПЕРВЫЙ ОТСКОК",
}

SETUP_STATE_LABELS = {
    "READY": "ГОТОВ",
    "WATCH": "НАБЛЮДЕНИЕ",
    "CONFIRMED": "ПОДТВЕРЖДЁН",
    "WAIT": "ОЖИДАНИЕ",
}

RS_LABELS = {
    "STRONGER": "СИЛЬНЕЕ РЫНКА",
    "WEAKER": "СЛАБЕЕ РЫНКА",
    "NEUTRAL": "НЕЙТРАЛЬНО",
    "UNAVAILABLE": "RS НЕДОСТУПЕН",
}


def _label(mapping, value):
    text = str(value or "-").upper()
    return mapping.get(text, value or "-")


def _money(value):
    try:
        return f"{float(value or 0):,.0f} ₽".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _number(value, digits=2):
    try:
        return f"{float(value or 0):,.{digits}f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _rs_label(item):
    status = str(item.get("relative_strength_status") or "").upper()
    if status not in {"OK", "AVAILABLE"}:
        return RS_LABELS["UNAVAILABLE"]

    signal = str(item.get("relative_strength_signal") or "NEUTRAL").upper()
    return RS_LABELS.get(signal, signal)


class TraderWindow(QWidget):
    """Large, scanner-only morning dashboard. No risk or execution controls."""

    def __init__(self, scanner_enabled=True):
        super().__init__()
        self.setWindowTitle("Trader_7_12 Pro — Утренний радар")
        self.resize(1120, 760)
        self.scanner = None
        self.scanner_enabled = scanner_enabled
        self.init_ui()

    def init_ui(self):
        self.title = QLabel("TRADER_7_12 PRO")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 30px; font-weight: 800; padding: 12px;")

        self.subtitle = QLabel(
            "УТРЕННИЙ РАДАР • 07:00–10:00 МСК • ДОПОЛНИТЕЛЬНО 10:00–13:00"
        )
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("font-size: 16px; font-weight: 600; padding: 4px;")

        self.scan_button = QPushButton("🔎  СКАНИРОВАТЬ РЫНОК")
        self.scan_button.setMinimumHeight(58)
        self.scan_button.setStyleSheet(
            "font-size: 20px; font-weight: 800; padding: 10px;"
        )
        self.scan_button.clicked.connect(self.run_market_scan)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet(
            "font-size: 18px; line-height: 1.35; padding: 12px;"
        )

        if not self.scanner_enabled:
            self.scan_button.setEnabled(False)
            self.result_box.setText(
                "👁  РЕЖИМ ПРОСМОТРА\n\n"
                "БКС временно недоступен.\n"
                "Сканирование будет доступно после восстановления подключения."
            )
        else:
            self.result_box.setText(
                "✅  БКС ПОДКЛЮЧЁН\n\n"
                "Нажмите «СКАНИРОВАТЬ РЫНОК».\n"
                "Сканер выберет TOP 2–3 фьючерса, где есть ликвидность, сила/слабость и потенциал движения."
            )

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.result_box)
        self.setLayout(layout)

    def run_market_scan(self):
        if not self.scanner_enabled:
            self.result_box.setText(
                "👁  РЕЖИМ ПРОСМОТРА\n\n"
                "БКС временно недоступен. Сканирование невозможно."
            )
            return

        self.result_box.setText(
            "📡  СКАНИРУЮ РЫНОК...\n\n"
            "СПОТ → ЛИКВИДНОСТЬ → СИЛА/СЛАБОСТЬ → УРОВНИ/СЕТАП → ФЬЮЧЕРС → TOP 2–3"
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
                "❌  ОШИБКА СКАНИРОВАНИЯ\n\n"
                f"{exc}"
            )
            self.scan_button.setEnabled(True)
            return

        self.scan_button.setEnabled(True)

        if not results:
            self.result_box.setText(
                "🌙  ГОТОВЫХ КАНДИДАТОВ НЕТ\n\n"
                "Ни один инструмент не прошёл все обязательные проверки."
            )
            return

        output = [
            "═" * 78,
            "TRADER_7_12 PRO — TOP 2–3 ФЬЮЧЕРСА",
            "═" * 78,
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ ЕСТЬ ПОТЕНЦИАЛ ДВИЖЕНИЯ",
            "",
        ]

        for index, item in enumerate(results, 1):
            direction = str(item.get("direction") or "-").upper()
            rs_signal = str(item.get("relative_strength_signal") or "UNAVAILABLE").upper()
            change = item.get("price_change_percent", 0)
            output.extend([
                "",
                f"████  #{index}  {item.get('futures_ticker', '-')}  /  {item.get('spot_ticker', '-')}  ████",
                f"НАПРАВЛЕНИЕ:     {_label(DIRECTION_LABELS, direction)}",
                f"ОЦЕНКА:          {_number(item.get('candidate_score'), 1)} / 100",
                f"RS:              {_rs_label(item)}",
                f"СЕТАП:           {_label(SETUP_LABELS, item.get('setup'))}",
                f"СОСТОЯНИЕ:        {_label(SETUP_STATE_LABELS, item.get('setup_state'))}",
                "",
                f"SPOT ЦЕНА:        {_number(item.get('spot_price'), 4)}",
                f"ФЬЮЧЕРС ЦЕНА:     {_number(item.get('futures_price'), 4)}",
                f"SPOT СРЕДНИЙ ₽×V: {_money(item.get('average_daily_money'))}",
                f"ФЬЮЧЕРС ₽×V:      {_money(item.get('money_volume'))}",
                f"СДЕЛОК:           {int(item.get('trade_count', 0) or 0):,}".replace(",", " "),
                f"ДВИЖЕНИЕ ФЬЮЧЕРСА: {_number(change, 2)}%",
                "",
                f"ЛОКАЛЬНЫЙ МАКСИМУМ: {_number(item.get('previous_high'), 4)}",
                f"ЛОКАЛЬНЫЙ МИНИМУМ:  {_number(item.get('previous_low'), 4)}",
                f"ТРИГГЕР УРОВНЯ:     {_number(item.get('entry_trigger'), 4)}",
                "",
                f"RS SIGNAL:         {RS_LABELS.get(rs_signal, rs_signal)}",
                "─" * 78,
            ])

        output.extend([
            "",
            "ВАЖНО: это АНАЛИТИЧЕСКИЙ РАДАР.",
            "Пользователь самостоятельно смотрит график и принимает решение о входе.",
            "Никакого position sizing, SL/TP или исполнения ордеров нет.",
        ])

        self.result_box.setText("\n".join(output))
