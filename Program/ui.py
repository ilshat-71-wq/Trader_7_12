"""Trader_7_12 Pro — professional, session-aware morning radar UI."""

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from services.market_session_service import MarketSessionService

DIRECTION_LABELS = {"LONG": "ЛОНГ", "SHORT": "ШОРТ"}
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
SESSION_LABELS = {
    "PRE_OPEN": "🟡  ПРЕ-ОТКРЫТИЕ",
    "MORNING": "🟢  УТРЕННЯЯ СЕССИЯ",
    "MAIN": "🔵  ОСНОВНАЯ СЕССИЯ",
    "EVENING": "🟣  ВЕЧЕРНЯЯ СЕССИЯ",
    "CLOSED": "⚫  РЫНОК ЗАКРЫТ",
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


class MarketScanWorker(QObject):
    """Run the blocking BCS scan outside the Qt GUI thread."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner, limit=3):
        super().__init__()
        self.scanner = scanner
        self.limit = limit

    def run(self):
        try:
            self.finished.emit(self.scanner.scan(limit=self.limit))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class TraderWindow(QWidget):
    """Read-only radar with live Moscow clock and session-aware presentation."""

    def __init__(self, scanner_enabled=True):
        super().__init__()
        self.setWindowTitle("Trader_7_12 Pro — Утренний радар")
        self.resize(1120, 800)
        self.scanner = None
        self.scanner_enabled = scanner_enabled
        self.scan_thread = None
        self.scan_worker = None
        self.session_service = MarketSessionService()
        self.animation_step = 0
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_session_header)
        self.scan_animation_timer = QTimer(self)
        self.scan_animation_timer.timeout.connect(self._animate_scan)
        self.init_ui()
        self.clock_timer.start(1000)
        self._update_session_header()

    def init_ui(self):
        self.title = QLabel("TRADER_7_12 PRO")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 30px; font-weight: 800; padding: 10px;")

        self.subtitle = QLabel("АНАЛИТИЧЕСКИЙ РАДАР • ВСЕ СЕССИИ MOEX • ВРЕМЯ МОСКОВСКОЕ")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("font-size: 15px; font-weight: 600; padding: 2px;")

        self.session_label = QLabel()
        self.session_label.setAlignment(Qt.AlignCenter)
        self.session_label.setStyleSheet("font-size: 21px; font-weight: 800; padding: 8px;")

        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("font-size: 15px; font-weight: 600; padding: 2px;")

        self.scan_status = QLabel("● ГОТОВ К СКАНИРОВАНИЮ")
        self.scan_status.setAlignment(Qt.AlignCenter)
        self.scan_status.setMinimumHeight(42)
        self.scan_status.setStyleSheet(
            "font-size: 18px; font-weight: 800; padding: 7px; border-radius: 8px;"
        )

        self.scan_button = QPushButton("🔎  СКАНИРОВАТЬ РЫНОК")
        self.scan_button.setMinimumHeight(58)
        self.scan_button.setStyleSheet("font-size: 20px; font-weight: 800; padding: 10px;")
        self.scan_button.clicked.connect(self.run_market_scan)

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setStyleSheet("font-size: 17px; padding: 12px;")

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
                "Радар выберет TOP 2–3 наиболее интересных фьючерса."
            )

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.session_label)
        layout.addWidget(self.clock_label)
        layout.addWidget(self.scan_status)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.result_box)
        self.setLayout(layout)

    def _update_session_header(self):
        info = self.session_service.get_session_info()
        session = info.get("session", "CLOSED")
        self.session_label.setText(SESSION_LABELS.get(session, session))
        market_state = "РЫНОК ОТКРЫТ" if info.get("market_open") else "РЫНОК ЗАКРЫТ"
        self.clock_label.setText(
            f"{info.get('date', '—')}  •  МСК {info.get('time', '—')}  •  {market_state}"
        )
        if session == "EVENING":
            self.subtitle.setText("ВЕЧЕРНИЙ РАДАР • 19:00–23:50 МСК • SPOT → RS → SETUP → FUTURES")
        elif session == "MORNING":
            self.subtitle.setText("УТРЕННИЙ РАДАР • 07:00–10:00 МСК • ОСНОВНОЕ ОКНО")
        elif session == "MAIN":
            self.subtitle.setText("ОСНОВНАЯ СЕССИЯ • 10:00–19:00 МСК • КОНТРОЛЬ РЫНКА")
        elif session == "PRE_OPEN":
            self.subtitle.setText("ПРЕ-ОТКРЫТИЕ • 06:50–07:00 МСК • ПОДГОТОВКА")
        else:
            self.subtitle.setText("РЫНОК ЗАКРЫТ • 23:50–06:50 МСК")

    def _animate_scan(self):
        self.animation_step = (self.animation_step + 1) % 4
        dots = "." * self.animation_step
        phase = [
            ("#6a1b9a", "#f3e5f5"),
            ("#7b1fa2", "#ede7f6"),
            ("#8e24aa", "#f3e5f5"),
            ("#9c27b0", "#ede7f6"),
        ][self.animation_step]
        self.scan_status.setText(f"🔎  СКАНИРОВАНИЕ РЫНКА{dots}  •  ПРОЦЕСС ИДЁТ")
        self.scan_status.setStyleSheet(
            f"font-size: 18px; font-weight: 800; padding: 7px; border-radius: 8px; "
            f"color: {phase[0]}; background: {phase[1]};"
        )

    def _start_scan_animation(self):
        self.animation_step = 0
        self.scan_animation_timer.start(220)
        self._animate_scan()

    def _stop_scan_animation(self, text="● СКАНИРОВАНИЕ ЗАВЕРШЕНО"):
        self.scan_animation_timer.stop()
        self.scan_status.setText(text)
        self.scan_status.setStyleSheet(
            "font-size: 18px; font-weight: 800; padding: 7px; border-radius: 8px;"
        )

    def run_market_scan(self):
        if not self.scanner_enabled:
            self.result_box.setText("👁  РЕЖИМ ПРОСМОТРА\n\nБКС временно недоступен.")
            return
        if self.scan_thread is not None and self.scan_thread.isRunning():
            return

        info = self.session_service.get_session_info()
        session = info.get("session", "CLOSED")
        session_name = SESSION_LABELS.get(session, session)
        self.result_box.setText(
            f"📡  {session_name}\n"
            f"МСК {info.get('time', '—')}\n\n"
            "SPOT → ЛИКВИДНОСТЬ → СИЛА/СЛАБОСТЬ → SETUP → FUTURES\n\n"
            "⏳ Анализ выполняется в фоне. Окно остаётся доступным."
        )
        self.scan_button.setEnabled(False)
        self.scan_button.setText("⏳  СКАНИРОВАНИЕ...")
        self._start_scan_animation()

        try:
            if self.scanner is None:
                from services.morning_trading_pipeline_service import MorningTradingPipelineService
                self.scanner = MorningTradingPipelineService()

            self.scan_thread = QThread(self)
            self.scan_worker = MarketScanWorker(self.scanner, limit=3)
            self.scan_worker.moveToThread(self.scan_thread)
            self.scan_thread.started.connect(self.scan_worker.run)
            self.scan_worker.finished.connect(self._scan_finished)
            self.scan_worker.failed.connect(self._scan_failed)
            self.scan_worker.finished.connect(self.scan_thread.quit)
            self.scan_worker.failed.connect(self.scan_thread.quit)
            self.scan_thread.finished.connect(self._scan_thread_finished)
            self.scan_thread.start()
        except Exception as exc:
            self._scan_failed(f"{type(exc).__name__}: {exc}")

    def _scan_finished(self, results):
        self.scan_button.setEnabled(True)
        self.scan_button.setText("🔎  СКАНИРОВАТЬ РЫНОК")
        self._stop_scan_animation()

        info = self.session_service.get_session_info()
        session_name = SESSION_LABELS.get(info.get("session"), info.get("session"))

        if not results:
            self.result_box.setText(
                f"{session_name}\nМСК {info.get('time', '—')}\n\n"
                "🌙  ГОТОВЫХ КАНДИДАТОВ НЕТ\n\n"
                "Ни один инструмент не прошёл обязательные проверки в текущей сессии."
            )
            return

        output = [
            "═" * 78,
            "TRADER_7_12 PRO — TOP 2–3 ФЬЮЧЕРСА",
            "═" * 78,
            "",
            f"{session_name} • {info.get('date', '—')} • МСК {info.get('time', '—')}",
            "",
            "ГДЕ ДЕНЬГИ • ГДЕ СИЛА/СЛАБОСТЬ • ГДЕ ЕСТЬ ПОТЕНЦИАЛ ДВИЖЕНИЯ",
            "",
        ]

        for index, item in enumerate(results, 1):
            direction = str(item.get("direction") or "-").upper()
            change = item.get("price_change_percent", 0)
            trigger = item.get("entry_trigger")
            if not trigger or float(trigger or 0) == 0:
                trigger = item.get("previous_high") if direction == "LONG" else item.get("previous_low")
            output.extend([
                "",
                f"████  #{index}  {item.get('futures_ticker', '-')}  /  {item.get('spot_ticker', '-')}  ████",
                f"НАПРАВЛЕНИЕ:      {_label(DIRECTION_LABELS, direction)}",
                f"ОЦЕНКА:           {_number(item.get('candidate_score'), 1)} / 100",
                f"RS:               {_rs_label(item)}",
                f"СЕТАП:            {_label(SETUP_LABELS, item.get('setup'))}",
                f"СОСТОЯНИЕ:         {_label(SETUP_STATE_LABELS, item.get('setup_state'))}",
                "",
                f"SPOT ЦЕНА:         {_number(item.get('spot_price'), 4)}",
                f"ФЬЮЧЕРС ЦЕНА:      {_number(item.get('futures_price'), 4)}",
                f"SPOT СРЕДНИЙ ₽×V:  {_money(item.get('spot_average_daily_money', item.get('average_daily_money')))}",
                f"ФЬЮЧЕРС ₽×V:       {_money(item.get('money_volume'))}",
                f"СДЕЛОК:            {int(item.get('trade_count', 0) or 0):,}".replace(",", " "),
                f"ДВИЖЕНИЕ ФЬЮЧЕРСА: {_number(change, 2)}%",
                "",
                f"ЛОКАЛЬНЫЙ МАКСИМУМ: {_number(item.get('previous_high'), 4)}",
                f"ЛОКАЛЬНЫЙ МИНИМУМ:  {_number(item.get('previous_low'), 4)}",
                f"ТРИГГЕР УРОВНЯ:     {_number(trigger, 4)}",
                "",
                "─" * 78,
            ])

        output.extend([
            "",
            "ВАЖНО: это АНАЛИТИЧЕСКИЙ РАДАР.",
            "Пользователь самостоятельно смотрит график и принимает решение о входе.",
            "Никакого position sizing, SL/TP или исполнения ордеров нет.",
        ])
        self.result_box.setText("\n".join(output))

    def _scan_failed(self, error):
        self.scan_button.setEnabled(True)
        self.scan_button.setText("🔎  СКАНИРОВАТЬ РЫНОК")
        self._stop_scan_animation("❌ СКАНИРОВАНИЕ ЗАВЕРШИЛОСЬ ОШИБКОЙ")
        self.result_box.setText(
            "❌  ОШИБКА СКАНИРОВАНИЯ\n\n"
            f"{error}\n\n"
            "БКС мог временно не ответить. Повторите сканирование."
        )

    def _scan_thread_finished(self):
        if self.scan_worker is not None:
            self.scan_worker.deleteLater()
        if self.scan_thread is not None:
            self.scan_thread.deleteLater()
        self.scan_worker = None
        self.scan_thread = None

    def closeEvent(self, event):
        self.scan_animation_timer.stop()
        self.clock_timer.stop()
        if self.scan_thread is not None and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait(3000)
        event.accept()
