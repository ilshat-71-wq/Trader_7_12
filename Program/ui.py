"""Trader_7_12 Pro — unified read-only market-information radar UI."""

from PySide6.QtCore import QThread, QTimer, Qt, QObject, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QLabel, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QTableWidgetItem

from services.market_attention_scanner_service import MarketAttentionScannerService
from services.market_session_service import MarketSessionService
from ui_table import MarketTableWidget, numeric

ROLE_LABELS = {
    "LONG_CANDIDATE": "ЛИДЕР",
    "SHORT_CANDIDATE": "АУТСАЙДЕР",
    "ATTENTION_WATCH": "НАБЛЮДЕНИЕ",
    "MARKET_CONTEXT": "КОНТЕКСТ",
}
SESSION_LABELS = {
    "PRE_OPEN": "ПРЕ-ОТКРЫТИЕ", "MORNING": "УТРЕННЯЯ СЕССИЯ",
    "MAIN": "ОСНОВНАЯ СЕССИЯ", "EVENING": "ВЕЧЕРНЯЯ СЕССИЯ",
    "WEEKEND_SESSION": "ДСВД", "CLOSED": "РЫНОК ЗАКРЫТ",
}
SCAN_COLORS = ("#9fba5d", "#b7d96b", "#d0e58a", "#b7d96b")
NEUTRAL_COLOR = "#c9d0d6"


def _number(value, digits=2):
    try:
        return f"{float(value or 0):,.{digits}f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _money(value):
    try:
        return f"{float(value or 0):,.0f} ₽".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


class MeltingClocksWidget(QWidget):
    """Compatibility widget; main.py replaces it with PremiumScanVisual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.setMinimumHeight(300)

    def start(self):
        self.update()

    def stop(self):
        self.timer.stop()


class MarketScanWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, scanner, limit=20):
        super().__init__()
        self.scanner = scanner
        self.limit = limit

    def run(self):
        try:
            results = self.scanner.scan(limit=self.limit)
            self.finished.emit(results, getattr(self.scanner, "_last_scan_diagnostics", {}))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class TraderWindow(QWidget):
    """Unified read-only D1-led SPOT market-information radar."""

    RADAR_LIMIT = 20

    def __init__(self, scanner_enabled=True):
        super().__init__()
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.resize(1280, 980)
        self.setMinimumSize(1120, 900)
        self.scanner = MarketAttentionScannerService() if scanner_enabled else None
        self.scanner_enabled = scanner_enabled
        self.scan_thread = None
        self.scan_worker = None
        self.session_service = MarketSessionService()
        self.animation_step = 0
        self._last_diagnostics = None
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_session_header)
        self.scan_animation_timer = QTimer(self)
        self.scan_animation_timer.timeout.connect(self._animate_scan)
        self.init_ui()
        self.clock_timer.start(1000)
        self._update_session_header()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background:#20252b; color:#e6e9ed; font-family:'Helvetica Neue',Arial,sans-serif; }
            QLabel { color:#e6e9ed; }
            QPushButton { background:#30373f; color:#f0f2f4; border:1px solid #46505a; border-radius:8px; padding:10px 18px; }
            QPushButton:hover { background:#38414a; }
            QPushButton:disabled { background:#30372e; border:1px solid #59634a; }
            QTextEdit { background:#171b20; color:#dfe3e7; border:1px solid #394149; border-radius:8px; padding:9px 12px; }
        """)

        self.title = QLabel("TRADER_7_12 PRO")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size:29px;font-weight:800;letter-spacing:1px;padding:8px")

        self.subtitle = QLabel("D1 • MARKET MAP • DAY MONEY FLOW • RS • FUTURES OI • READ-ONLY")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("font-size:13px;color:#89939d;padding:1px")

        self.session_label = QLabel()
        self.session_label.hide()
        self.clock_label = QLabel()
        self.clock_label.hide()

        self.scan_button = QPushButton("●  СКАНИРОВАТЬ РЫНОК")
        self.scan_button.setMinimumHeight(54)
        self.scan_button.clicked.connect(self.run_market_scan)
        self._set_scan_button_style()

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setFixedHeight(132)
        self.result_box.setStyleSheet("font-size:13px;font-weight:600")

        self.result_table = MarketTableWidget(
            ["#", "Ticker", "Role", "D1", "D1-RS", "IDX Δ%", "Price Δ%", "RS", "₽/min", "DAY ₽", "15m", "Accel", "Score"],
            [42, 76, 118, 88, 68, 72, 82, 72, 92, 112, 92, 72, 68],
        )

        self.result_panel = QWidget()
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(6)
        result_layout.addWidget(self.result_box)
        result_layout.addWidget(self.result_table, 1)
        self.result_table.hide()

        self.scan_visual = MeltingClocksWidget()
        self.result_stack = QStackedWidget()
        self.result_stack.addWidget(self.result_panel)
        self.result_stack.addWidget(self.scan_visual)
        self.result_stack.setCurrentWidget(self.result_panel)

        self.scan_button.setEnabled(self.scanner_enabled)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 10, 18, 18)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.scan_button)
        layout.addWidget(self.result_stack, 1)
        self.setLayout(layout)

        if self.scanner_enabled:
            self.result_box.setPlainText("БКС ПОДКЛЮЧЁН • Нажмите «СКАНИРОВАТЬ РЫНОК».")
        else:
            self.result_box.setPlainText("РЕЖИМ ПРОСМОТРА • БКС временно недоступен.")

    def _set_scan_button_style(self, color=NEUTRAL_COLOR):
        self.scan_button.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{color};background:#30373f;"
            "border:1px solid #46505a;border-radius:8px;padding:10px 18px"
        )

    def _update_session_header(self):
        info = self.session_service.get_session_info()
        session = info.get("session", "CLOSED")
        self.session_label.setText(SESSION_LABELS.get(session, session))
        state = "РЫНОК ОТКРЫТ" if info.get("market_open") else "РЫНОК ЗАКРЫТ"
        self.clock_label.setText(f"{info.get('date','—')} • МСК {info.get('time','—')} • {state}")
        if self._last_diagnostics is None:
            self.result_box.setPlainText(
                f"{SESSION_LABELS.get(session, session)} • {info.get('date','—')} • "
                f"МСК {info.get('time','—')} • {state}"
            )

    def _animate_scan(self):
        self.animation_step = (self.animation_step + 1) % len(SCAN_COLORS)
        self.scan_button.setText("●  ИДЁТ АНАЛИЗ D1 + M5 + RS")
        self._set_scan_button_style(SCAN_COLORS[self.animation_step])

    def _start_scan_animation(self):
        self.scan_visual.start()
        self.result_stack.setCurrentWidget(self.scan_visual)
        self.scan_animation_timer.start(260)
        self._animate_scan()

    def _stop_scan_animation(self):
        self.scan_animation_timer.stop()
        self.scan_visual.stop()
        self.scan_button.setText("●  СКАНИРОВАТЬ РЫНОК")
        self._set_scan_button_style()
        self.result_stack.setCurrentWidget(self.result_panel)

    @staticmethod
    def _skip_summary(diagnostics):
        reasons = diagnostics.get("skip_reasons") or {}
        if not reasons:
            return "нет"
        labels = {
            "INSUFFICIENT_M5": "M5", "LOW_LIQUIDITY": "LOW LIQUIDITY",
            "D1_UNAVAILABLE": "D1", "WORKER_ERROR": "ERROR", "INVALID_RESULT": "INVALID",
        }
        return " • ".join(f"{labels.get(k, k)} {v}" for k, v in reasons.items())

    @staticmethod
    def _empty_reason(diagnostics):
        regime = str(diagnostics.get("market_regime") or "").upper()
        coverage = diagnostics.get("coverage_percent")
        if regime == "NEUTRAL":
            return "РЫНОК NEUTRAL — строгий Long/Short по контракту не формируется; ниже показан объективный контекст рынка."
        if coverage is not None and float(coverage) < 80.0:
            return "Недостаточное M5-покрытие для строгой directional-оценки."
        if diagnostics.get("daily_profiles_qualified", 0) == 0:
            return "Нет достаточного D1 quality для строгих кандидатов."
        if diagnostics.get("liquidity_passed", 0) == 0:
            return "Нет инструментов, прошедших оба абсолютных liquidity-gate."
        return "Нет инструмента, одновременно прошедшего все strict-gates."

    @staticmethod
    def _apply_relative_strength_tint(table, row_index, relative_strength):
        """Tint by current intraday relative strength versus IMOEX2."""
        try:
            rs = float(relative_strength)
        except (TypeError, ValueError):
            return

        if rs > 0.01:
            background = QColor("#20382b")
            foreground = QColor("#bfe8c8")
        elif rs < -0.01:
            background = QColor("#3a272b")
            foreground = QColor("#f0b9bf")
        else:
            return

        for column in range(table.columnCount()):
            item = table.item(row_index, column)
            if item is not None:
                item.setBackground(background)
                item.setForeground(foreground)

    def run_market_scan(self):
        if not self.scanner_enabled or (self.scan_thread is not None and self.scan_thread.isRunning()):
            return
        self.scan_button.setEnabled(False)
        self._start_scan_animation()
        try:
            self.scan_thread = QThread(self)
            self.scan_worker = MarketScanWorker(self.scanner, limit=self.RADAR_LIMIT)
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

    def _scan_finished(self, results, diagnostics):
        self.scan_button.setEnabled(True)
        self._stop_scan_animation()
        self._last_diagnostics = diagnostics or {}
        info = self.session_service.get_session_info()
        session_name = SESSION_LABELS.get(info.get("session", "CLOSED"), "РЫНОК")
        benchmark = str(diagnostics.get("benchmark") or "—")
        line1 = f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')} • INTRADAY 07:00→NOW"
        line2 = (
            f"{diagnostics.get('status') or '—'} • {benchmark} • UNIVERSE {diagnostics.get('universe_total', 0)} • "
            f"ANALYZED {diagnostics.get('analyzed', 0)} • COVERAGE {_number(diagnostics.get('coverage_percent'), 1)}%"
        )
        line3 = (
            f"D1 {_number(diagnostics.get('daily_benchmark_days'), 0)} • QUALIFIED {diagnostics.get('daily_profiles_qualified', 0)} • "
            f"LIQUIDITY {diagnostics.get('liquidity_passed', 0)} • STRICT {diagnostics.get('strict_selected', 0)} • "
            f"WATCH {diagnostics.get('watch_selected', 0)} • CONTEXT {diagnostics.get('context_selected', 0)} • REGIME {diagnostics.get('market_regime') or '—'}"
        )
        rows = []
        rs_values = []
        for idx, item in enumerate(results or [], 1):
            role = ROLE_LABELS.get(str(item.get("selection_role") or "").upper(), "КОНТЕКСТ")
            if item.get("qualification_status") == "WATCH_ONLY":
                role = "НАБЛЮДЕНИЕ"
            rs = item.get("relative_strength")
            rs_values.append(rs)
            rows.append([
                numeric(idx), str(item.get("spot_ticker") or "—"), role,
                str(item.get("daily_structure") or "NEUTRAL")[:10],
                numeric(_number(item.get("daily_relative_mean_pp"), 2)),
                numeric(_number(item.get("benchmark_change_percent"), 2)),
                numeric(_number(item.get("change_percent"), 2)),
                numeric(_number(rs, 2)),
                numeric(_money(item.get("money_per_minute"))),
                numeric(_money(item.get("day_money", item.get("session_money")))),
                numeric(_money(item.get("recent_money"))),
                numeric(f"{_number(item.get('money_acceleration'), 1)}%"),
                numeric(_number(item.get("directional_score"), 1)),
            ])
        self.result_table.set_rows(rows)
        for row_index, rs in enumerate(rs_values):
            self._apply_relative_strength_tint(self.result_table, row_index, rs)
        self.result_table.setToolTip(
            "Зелёный оттенок — инструмент сильнее IMOEX2; красный — слабее IMOEX2. "
            "DAY ₽ — накопленный денежный оборот с 07:00 МСК до момента сканирования. "
            "Выделите строки и нажмите ⌘C для TSV."
        )
        self.result_table.setVisible(bool(rows))
        if rows:
            self.result_box.setPlainText("\n".join((line1, line2, line3)))
        else:
            line4 = self._empty_reason(diagnostics)
            line5 = f"ПРОПУСКИ: {self._skip_summary(diagnostics)}"
            self.result_box.setPlainText("\n".join((line1, line2, line3, line4, line5)))

    def _scan_failed(self, error):
        self.scan_button.setEnabled(True)
        self._stop_scan_animation()
        self.result_table.hide()
        self.result_box.setPlainText(f"ОШИБКА СКАНИРОВАНИЯ\n\n{error}")

    def _scan_thread_finished(self):
        if self.scan_thread is not None:
            self.scan_thread.deleteLater()
        self.scan_thread = None
        self.scan_worker = None
