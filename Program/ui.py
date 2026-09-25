"""Trader_7_12 Pro — professional unified read-only market-information radar UI."""

from PySide6.QtCore import QThread, QTimer, Qt, QObject, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.market_attention_scanner_service import MarketAttentionScannerService
from services.market_session_service import MarketSessionService
from ui_table import MarketTableWidget, numeric


ROLE_LABELS = {
    "LONG_CANDIDATE": "LEADER",
    "SHORT_CANDIDATE": "LAGGARD",
    "ATTENTION_WATCH": "WATCH",
    "MARKET_CONTEXT": "CONTEXT",
}
SESSION_LABELS = {
    "PRE_OPEN": "PRE-OPEN",
    "MORNING": "MORNING SESSION",
    "MAIN": "MAIN SESSION",
    "EVENING": "EVENING SESSION",
    "WEEKEND_SESSION": "WEEKEND",
    "CLOSED": "MARKET CLOSED",
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
        self.resize(1440, 960)
        self.setMinimumSize(1180, 760)

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
            QWidget {
                background: #20252b;
                color: #e6e9ed;
                font-family: 'Helvetica Neue', Arial, sans-serif;
            }
            QFrame#topBar {
                background: #171c21;
                border: 1px solid #394149;
                border-radius: 10px;
            }
            QFrame#statusCard {
                background: #20262c;
                border: 1px solid #353e46;
                border-radius: 7px;
            }
            QLabel { color: #e6e9ed; }
            QLabel#brand {
                font-size: 24px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#subtitle {
                color: #87929d;
                font-size: 11px;
            }
            QLabel#statusTitle {
                color: #7f8a94;
                font-size: 9px;
                font-weight: 700;
            }
            QLabel#statusValue {
                color: #e4e8eb;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#liveDot {
                color: #69e59a;
                font-size: 9px;
                font-weight: 800;
            }
            QLabel#microStatus {
                color: #6f7a84;
                font-size: 9px;
                font-weight: 700;
            }
            QPushButton {
                background: #30383f;
                color: #f0f2f4;
                border: 1px solid #4a555f;
                border-radius: 7px;
                padding: 8px 13px;
                font-weight: 700;
            }
            QPushButton:hover { background: #39434c; }
            QPushButton:pressed { background: #273037; }
            QPushButton:disabled {
                color: #8d969d;
                background: #2a302d;
                border-color: #465043;
            }
            QPushButton#primaryAction {
                min-height: 38px;
                font-size: 12px;
            }
            QPushButton#secondaryAction {
                min-height: 38px;
                font-size: 11px;
            }
            QTabWidget::pane {
                background: #171b20;
                border: 1px solid #394149;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #252c33;
                color: #9ea8b1;
                border: 1px solid #394149;
                border-bottom: 0;
                padding: 9px 16px;
                margin-right: 3px;
                min-width: 130px;
                font-size: 11px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: #303a42;
                color: #f0f2f4;
                border-top: 2px solid #d4af55;
            }
            QTextEdit {
                background: #171b20;
                color: #dfe3e7;
                border: 1px solid #394149;
                border-radius: 8px;
                padding: 9px 12px;
                selection-background-color: #33424a;
            }
        """)

        self._build_header()

        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)
        self.result_box.setFixedHeight(82)
        self.result_box.setStyleSheet(
            "font-size:11px;font-weight:600;background:#171b20;"
            "border:0;padding:7px 10px;"
        )
        self.result_box.setToolTip(
            "Market passport: session, coverage, selection and regime. "
            "The tables below are the market map."
        )

        columns = [
            "#", "Ticker", "Role", "D1", "D1-RS", "IDX Δ%", "Price Δ%", "ATR / USED",
            "RS", "₽/min", "DAY ₽", "15m", "Accel", "Score",
            "SIGNAL", "PROB", "ΔPROB", "BOOK", "TAPE", "FLOW RT",
        ]
        widths = [
            42, 78, 118, 88, 72, 78, 86, 94, 78, 104, 112, 98, 78, 72,
            78, 72, 72, 82, 82, 82,
        ]
        self.result_table = MarketTableWidget(columns, widths)
        self.weak_result_table = MarketTableWidget(columns, widths)

        self.spot_tabs = QTabWidget()
        self.spot_tabs.setDocumentMode(True)
        self.spot_tabs.addTab(self.result_table, "STRONGER THAN IMOEX2")
        self.spot_tabs.addTab(self.weak_result_table, "WEAKER THAN IMOEX2")
        self.spot_tabs.setToolTip(
            "SPOT split by relative strength versus IMOEX2"
        )

        self.result_panel = QWidget()
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(8, 8, 8, 8)
        result_layout.setSpacing(7)
        result_layout.addWidget(self.result_box)
        result_layout.addWidget(self.spot_tabs, 1)
        self.result_table.hide()
        self.weak_result_table.hide()

        self.scan_visual = MeltingClocksWidget()
        self.result_stack = QStackedWidget()
        self.result_stack.addWidget(self.result_panel)
        self.result_stack.addWidget(self.scan_visual)
        self.result_stack.setCurrentWidget(self.result_panel)

        self.market_tabs = QTabWidget()
        self.market_tabs.setDocumentMode(True)
        self.market_tabs.addTab(self.result_stack, "SPOT")
        self.diagnostics_panel = self._build_diagnostics_panel()
        self.market_tabs.addTab(self.diagnostics_panel, "DIAGNOSTICS")

        self.footer = self._build_footer()

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
        layout.addWidget(self.top_bar)
        layout.addWidget(self.market_tabs, 1)
        layout.addWidget(self.footer)
        self.setLayout(layout)

        if self.scanner_enabled:
            self.result_box.setPlainText(
                "START HERE  •  1) SCAN MARKET → market context  •  "
                "2) MORNING RADAR → WHO  •  3) ENTRY RADAR → WHEN / WHERE  •  "
                "4) FUTURES OI → WHY  •  5) BOOK / TAPE / FLOW RT → WHAT IS HAPPENING NOW."
            )
        else:
            self.result_box.setPlainText("VIEW-ONLY MODE • BCS temporarily unavailable.")

    def _build_header(self):
        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBar")
        top = QHBoxLayout(self.top_bar)
        top.setContentsMargins(14, 10, 14, 10)
        top.setSpacing(8)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(1)
        self.title = QLabel("TRADER_7_12 PRO")
        self.title.setObjectName("brand")
        self.subtitle = QLabel(
            "READ-ONLY MARKET RADAR  •  SPOT  •  D1 / M5  •  RS  •  MONEY FLOW  •  FUTURES OI  •  LIVE BOOK / TAPE"
        )
        self.subtitle.setObjectName("subtitle")
        brand_box.addWidget(self.title)
        brand_box.addWidget(self.subtitle)
        top.addLayout(brand_box, 1)

        self.bcs_status = self._status_card("DATA", "BCS • READY")
        self.session_status = self._status_card("SESSION", "—")
        self.session_status.setFixedWidth(150)
        self.coverage_status = self._status_card("COVERAGE", "—")
        top.addWidget(self.bcs_status)
        top.addWidget(self.session_status)
        top.addWidget(self.coverage_status)

        self.scan_button = QPushButton("SCAN MARKET")
        self.scan_button.setObjectName("primaryAction")
        self.scan_button.clicked.connect(self.run_market_scan)
        self._set_scan_button_style()
        top.addWidget(self.scan_button)

        self.guide_button = QPushButton("30 SEC GUIDE")
        self.guide_button.setObjectName("secondaryAction")
        self.guide_button.setToolTip("How to read Trader_7_12 Pro in 30 seconds")
        self.guide_button.clicked.connect(self._show_quick_guide)
        top.addWidget(self.guide_button)

        self.copy_button = QPushButton("COPY")
        self.copy_button.setObjectName("secondaryAction")
        self.copy_button.clicked.connect(self.copy_active_table)
        self.copy_button.setToolTip(
            "⌘C / Ctrl+C — selected rows; without selection — entire table"
        )
        top.addWidget(self.copy_button)

    def _show_quick_guide(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Trader_7_12 Pro — 30 Second Guide")
        dialog.setMinimumWidth(640)
        layout = QVBoxLayout(dialog)

        title = QLabel("TRADER_7_12 PRO • 30 SECOND GUIDE")
        title.setStyleSheet("font-size:18px;font-weight:800;color:#e8ecef;")
        layout.addWidget(title)

        body = QLabel(
            "<b>THE WORKFLOW</b><br>"
            "<b>1. MARKET RADAR</b> — what is happening across the market.<br>"
            "<b>2. MORNING RADAR</b> — WHO deserves attention before the main futures session.<br>"
            "<b>3. ENTRY RADAR</b> — WHEN / WHERE the existing model sees an entry setup.<br>"
            "<b>4. FUTURES OI</b> — WHY: price, open interest, turnover, flow, action and zone.<br>"
            "<b>5. BOOK / TAPE / FLOW RT</b> — WHAT is happening right now in the live market.<br><br>"
            "<b>READ THE STATES</b><br>"
            "<b>ENTER</b> = confidence ≥ 80% + valid zone.<br>"
            "<b>WAIT</b> = 65–79% + valid zone.<br>"
            "<b>WATCH</b> = incomplete or lower-confidence setup.<br>"
            "<b>AVOID</b> = no new entry is confirmed by the current structure; it does not mean the instrument is permanently bad.<br><br>"
            "<b>IMPORTANT</b><br>"
            "PROB is model confidence, not a guaranteed probability of profit. "
            "BOOK / TAPE / FLOW RT are observed realtime pressure scores, not probabilities. "
            "Trader_7_12 Pro is read-only and does not place orders."
        )
        body.setWordWrap(True)
        body.setStyleSheet(
            "background:#171b20;border:1px solid #394149;border-radius:8px;"
            "padding:12px;color:#c9d0d6;font-size:12px;"
        )
        layout.addWidget(body)

        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        close.accepted.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    @staticmethod
    def _status_card(title, value):
        card = QFrame()
        card.setObjectName("statusCard")
        card.setFixedWidth(118)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 5, 9, 5)
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("statusTitle")
        value_label = QLabel(value)
        value_label.setObjectName("statusValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.value_label = value_label
        return card

    def _build_footer(self):
        footer = QFrame()
        footer.setStyleSheet(
            "QFrame{background:#171b20;border:1px solid #394149;border-radius:7px;}"
            "QLabel{color:#7f8a94;font-size:10px;}"
        )
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(18)
        left = QLabel("READ-ONLY  •  REAL DATA ONLY  •  NO ORDER EXECUTION")
        left.setObjectName("microStatus")
        live = QLabel("● LIVE")
        live.setObjectName("liveDot")
        live.setToolTip("Live market-data presentation layer")
        right = QLabel("BCS SPOT  +  MOEX RFUD FUTURES/OI")
        right.setObjectName("microStatus")
        layout.addWidget(left)
        layout.addStretch(1)
        layout.addWidget(right)
        layout.addWidget(live)
        return footer

    def _build_diagnostics_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.diagnostics_box = QTextEdit()
        self.diagnostics_box.setReadOnly(True)
        self.diagnostics_box.setFont(QFont("Menlo", 11))
        self.diagnostics_box.setPlainText(
            "After scanning, technical data-source status will appear here, "
            "coverage, skips, and exclusion reasons.\n\n"
            "Project rule: missing data is shown as missing data; "
            "synthetic values are never used."
        )

        self.copy_diagnostics_button = QPushButton("COPY DIAGNOSTICS")
        self.copy_diagnostics_button.clicked.connect(
            lambda: QApplication.clipboard().setText(self.diagnostics_box.toPlainText())
        )

        layout.addWidget(self.diagnostics_box, 1)
        layout.addWidget(self.copy_diagnostics_button, 0, Qt.AlignRight)
        return panel

    def _set_scan_button_style(self, color=NEUTRAL_COLOR):
        self.scan_button.setStyleSheet(
            f"font-size:12px;font-weight:800;color:{color};background:#30383f;"
            "border:1px solid #4a555f;border-radius:7px;padding:8px 14px;"
        )

    def _update_session_header(self):
        info = self.session_service.get_session_info()
        session = info.get("session", "CLOSED")
        state = "OPEN" if info.get("market_open") else "CLOSED"
        self.session_status.value_label.setText(
            f"{state} • {info.get('time', '—')}"
        )
        if self._last_diagnostics is None:
            self.result_box.setPlainText(
                f"{SESSION_LABELS.get(session, session)} • "
                f"{info.get('date', '—')} • MSK {info.get('time', '—')} • "
                f"MARKET {state}"
            )

    def _animate_scan(self):
        self.animation_step = (self.animation_step + 1) % len(SCAN_COLORS)
        self.scan_button.setText("ANALYZING  •  D1 + M5 + RS")
        self._set_scan_button_style(SCAN_COLORS[self.animation_step])

    def _start_scan_animation(self):
        self.scan_visual.start()
        self.result_stack.setCurrentWidget(self.scan_visual)
        self.scan_animation_timer.start(260)
        self._animate_scan()

    def _stop_scan_animation(self):
        self.scan_animation_timer.stop()
        self.scan_visual.stop()
        self.scan_button.setText("●  SCAN MARKET")
        self._set_scan_button_style()
        self.result_stack.setCurrentWidget(self.result_panel)

    @staticmethod
    def _skip_summary(diagnostics):
        reasons = diagnostics.get("skip_reasons") or {}
        if not reasons:
            return "none"
        labels = {
            "INSUFFICIENT_M5": "M5",
            "LOW_LIQUIDITY": "LOW LIQUIDITY",
            "D1_UNAVAILABLE": "D1",
            "WORKER_ERROR": "ERROR",
            "INVALID_RESULT": "INVALID",
        }
        return " • ".join(
            f"{labels.get(k, k)} {v}" for k, v in reasons.items()
        )

    @staticmethod
    def _empty_reason(diagnostics):
        regime = str(diagnostics.get("market_regime") or "").upper()
        coverage = diagnostics.get("coverage_percent")
        if regime == "NEUTRAL":
            return (
                "MARKET NEUTRAL — no strict Long/Short setup is generated; "
                "the objective market context is shown below."
            )
        if coverage is not None and float(coverage) < 80.0:
            return "Insufficient M5 coverage for a strict directional assessment."
        if diagnostics.get("daily_profiles_qualified", 0) == 0:
            return "Insufficient D1 quality for strict candidates."
        if diagnostics.get("liquidity_passed", 0) == 0:
            return "No instruments passed both absolute liquidity gates."
        return "No instrument passed all strict gates."

    @staticmethod
    def _signal_label(signal):
        signal = str(signal or "").upper()
        return {
            "LONG": "🟢 LONG",
            "SHORT": "🔴 SHORT",
            "NEUTRAL": "⚪ NEUTRAL",
        }.get(signal, "⚪ —")

    @staticmethod
    def _direction_row_brush(change_percent):
        try:
            change = float(change_percent)
        except (TypeError, ValueError):
            return None
        if change > 0:
            return QBrush(QColor("#123f2a"))
        if change < 0:
            return QBrush(QColor("#3a272b"))
        return None

    @classmethod
    def _apply_spot_direction_colors(cls, table, prepared_results):
        for row_index, item in enumerate(prepared_results):
            brush = cls._direction_row_brush(item.get("change_percent"))
            if brush is None:
                continue
            for col in range(table.columnCount()):
                cell = table.item(row_index, col)
                if cell:
                    cell.setBackground(brush)

    @classmethod
    def _apply_signal_colors(cls, table, prepared_results):
        # Direction is carried by a premium-style colored dot; the text and
        # probability remain neutral so color has one unambiguous meaning.
        for row_index, item in enumerate(prepared_results):
            signal = str(item.get("signal") or "")
            signal_cell = table.item(row_index, 13)
            if signal_cell:
                signal_cell.setText(cls._signal_label(signal))
                signal_cell.setForeground(QColor("#e6e9ed"))
            for col in (14, 15):
                cell = table.item(row_index, col)
                if cell:
                    cell.setForeground(QColor("#c9d0d6"))

    def _rows_for_results(self, results):
        rows = []
        for idx, item in enumerate(results or [], 1):
            role = ROLE_LABELS.get(
                str(item.get("selection_role") or "").upper(),
                "CONTEXT",
            )
            if item.get("qualification_status") == "WATCH_ONLY":
                role = "WATCH"

            rs = item.get("relative_strength")
            rows.append((
                float(rs) if rs is not None else 0.0,
                [
                    numeric(idx),
                    str(item.get("spot_ticker") or "—"),
                    role,
                    str(item.get("daily_structure") or "NEUTRAL")[:10],
                    numeric(_number(item.get("daily_relative_mean_pp"), 2)),
                    numeric(_number(item.get("benchmark_change_percent"), 2)),
                    numeric(_number(item.get("change_percent"), 2)),
                    numeric(
                        f"{_number(item.get('atr_percent'), 1)}% • {_number(item.get('atr_used_percent'), 0)}%"
                        if item.get("atr_percent") is not None and item.get("atr_used_percent") is not None
                        else "—"
                    ),
                    numeric(_number(rs, 2)),
                    numeric(_money(item.get("money_per_minute"))),
                    numeric(_money(item.get("day_money", item.get("session_money")))),
                    numeric(_money(item.get("recent_money"))),
                    numeric(f"{_number(item.get('money_acceleration'), 1)}%"),
                    numeric(_number(item.get("directional_score"), 1)),
                    str(item.get("signal") or "—"),
                    numeric(
                        f"{_number(item.get('signal_probability'), 1)}%"
                        if item.get("signal_probability") is not None else "—"
                    ),
                    numeric(
                        f"{_number(item.get('signal_probability_delta'), 1)}%"
                        if item.get("signal_probability_delta") is not None else "NEW"
                    ),
                    "—",
                    "—",
                    "—",
                ],
                item,
            ))
        return rows

    def _populate_spot_table(self, table, entries):
        rows = []
        items = []
        for index, (_rs, row, item) in enumerate(entries, 1):
            row = list(row)
            row[0] = numeric(index)
            rows.append(row)
            items.append(item)
        table.set_rows(rows)
        self._apply_spot_direction_colors(table, items)
        self._apply_signal_colors(table, items)
        table.setVisible(bool(rows))
        return len(rows)

    def run_market_scan(self):
        if not self.scanner_enabled or (
            self.scan_thread is not None and self.scan_thread.isRunning()
        ):
            return

        self.scan_button.setEnabled(False)
        self._start_scan_animation()

        try:
            self.scan_thread = QThread(self)
            self.scan_worker = MarketScanWorker(
                self.scanner, limit=self.RADAR_LIMIT
            )
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
        session_name = SESSION_LABELS.get(
            info.get("session", "CLOSED"), "MARKET"
        )
        benchmark = str(diagnostics.get("benchmark") or "—")

        line1 = (
            f"{session_name} • {info.get('date', '—')} • "
            f"MSK {info.get('time', '—')} • INTRADAY 07:00→NOW"
        )
        line2 = (
            f"{diagnostics.get('status') or '—'} • {benchmark} • "
            f"UNIVERSE {diagnostics.get('universe_total', 0)} • "
            f"ANALYZED {diagnostics.get('analyzed', 0)} • "
            f"COVERAGE {_number(diagnostics.get('coverage_percent'), 1)}%"
        )
        line3 = (
            f"D1 {diagnostics.get('daily_benchmark_days', 0)} • "
            f"QUALIFIED {diagnostics.get('daily_profiles_qualified', 0)} • "
            f"LIQUIDITY {diagnostics.get('liquidity_passed', 0)} • "
            f"STRICT {diagnostics.get('strict_selected', 0)} • "
            f"WATCH {diagnostics.get('watch_selected', 0)} • "
            f"CONTEXT {diagnostics.get('context_selected', 0)} • "
            f"REGIME {diagnostics.get('market_regime') or '—'}"
        )

        # The SPOT tabs are a market map, not a copy of the selected radar.
        # Keep realtime bounded to the strongest current relative-strength rows
        # from the same market map, rather than subscribing to the full universe.
        raw_market_map = diagnostics.get("market_map")
        market_map = (
            raw_market_map
            if isinstance(raw_market_map, list)
            else list(results or [])
        )
        if hasattr(self, "move_radar"):
            self.move_radar.set_results(market_map)
        entries = self._rows_for_results(market_map)
        self._spot_results_for_realtime = [
            entry[2]
            for entry in sorted(
                (
                    entry for entry in entries
                    if entry[2].get("spot_ticker")
                    and (
                        entry[2].get("spot_class_code")
                        or entry[2].get("class_code")
                    )
                ),
                key=lambda entry: abs(entry[0]),
                reverse=True,
            )[:30]
        ]

        # STRONGER/WEAKER are an independent relative-strength market map.
        # They are NOT the selected radar. Positive RS belongs in STRONGER,
        # negative RS belongs in WEAKER, regardless of market regime or
        # whether the row was selected as LONG/SHORT/WATCH.
        strong = sorted(
            (entry for entry in entries if entry[0] > 0.0),
            key=lambda entry: entry[0],
            reverse=True,
        )
        weak = sorted(
            (entry for entry in entries if entry[0] < 0.0),
            key=lambda entry: entry[0],
        )
        neutral = len(entries) - len(strong) - len(weak)

        strong_count = self._populate_spot_table(self.result_table, strong)
        weak_count = self._populate_spot_table(self.weak_result_table, weak)

        # Keep the diagnostic passport internally consistent. If the backend
        # reports a non-zero market map but the UI receives no rows, surface it
        # explicitly instead of silently showing an empty STRONGER tab.
        map_total = diagnostics.get("market_map_total", len(entries))
        map_stronger = diagnostics.get("market_map_stronger", strong_count)
        map_weaker = diagnostics.get("market_map_weaker", weak_count)

        regime = str(diagnostics.get("market_regime") or "NEUTRAL").upper()
        if regime == "UP":
            regime_note = (
                "INDEX UP: STRONGER = stocks rising more than IMOEX2; "
                "WEAKER = stocks rising less than IMOEX2 or falling."
            )
        elif regime == "DOWN":
            regime_note = (
                "INDEX DOWN: STRONGER = stocks rising or falling less than IMOEX2; "
                "WEAKER = stocks falling more than IMOEX2."
            )
        else:
            regime_note = (
                "INDEX NEUTRAL: tabs still use positive/negative RS; "
                "row color shows the stock's own price direction."
            )

        self.result_table.setToolTip(
            f"SPOT STRONGER THAN IMOEX2 — {regime_note} "
            "Green row = stock is rising; red row = stock is falling. "
            "ATR / USED = completed D1 ATR(14) as % of reference price • intraday move used as % of ATR; informational only. "
            "BOOK/TAPE/FLOW RT — live BCS WebSocket observed pressure scores; not probabilities. "
            "DAY ₽ — accumulated monetary turnover since 07:00 MSK."
        )
        self.weak_result_table.setToolTip(
            f"SPOT WEAKER THAN IMOEX2 — {regime_note} "
            "Green row = stock is rising; red row = stock is falling. "
            "ATR / USED = completed D1 ATR(14) as % of reference price • intraday move used as % of ATR; informational only. "
            "SIGNAL/PROB/ΔPROB retain their own LONG/SHORT/NEUTRAL colors. "
            "DAY ₽ — accumulated monetary turnover since 07:00 MSK."
        )

        self.coverage_status.value_label.setText(
            f"{_number(diagnostics.get('coverage_percent'), 0)}%"
        )

        split_note = (
            f"SPOT {regime} • MAP {map_total} • STRONGER {map_stronger}/{strong_count} • "
            f"WEAKER {map_weaker}/{weak_count} • RS NEUTRAL {neutral} • "
            f"ROW COLOR = PRICE DIRECTION"
        )
        self.result_box.setPlainText(
            "\n".join((line1, line2, line3, split_note))
        )

        self.diagnostics_box.setPlainText(self._format_diagnostics(diagnostics))
        self.market_tabs.setCurrentIndex(0)
        self.spot_tabs.setCurrentIndex(0 if strong_count else 1)

    @staticmethod
    def _format_diagnostics(diagnostics):
        """Render a compact operator passport; never dump raw internal maps."""
        if not diagnostics:
            return "No diagnostics available."

        def val(key, default="—"):
            value = diagnostics.get(key, default)
            return default if value is None or value == "" else value

        def num(key, digits=1):
            return _number(diagnostics.get(key), digits)

        lines = [
            "=== SPOT / MARKET RADAR ===",
            f"STATUS: {val('status')}   SESSION: {val('session')}   REGIME: {val('market_regime')}",
            f"TRADING DATE: {val('trading_date')}   PREFERRED WINDOW: {val('preferred_window_active')}",
            "",
            "COVERAGE",
            f"Universe {val('universe_total', 0)} • Analyzed {val('analyzed', 0)} • Coverage {num('coverage_percent')}%",
            f"Liquidity passed {val('liquidity_passed', 0)} • Filtered {val('liquidity_filtered', 0)}",
            f"D1 qualified {val('daily_profiles_qualified', 0)} • Directional qualified {val('directional_qualified', 0)}",
            "",
            "SELECTION",
            f"Strict {val('strict_selected', 0)} • Watch {val('watch_selected', 0)} • Context {val('context_selected', 0)} • Selected {val('selected', 0)}",
            f"Market map {val('market_map_total', 0)} • Stronger {val('market_map_stronger', 0)} • Weaker {val('market_map_weaker', 0)} • Neutral {val('market_map_neutral', 0)}",
            "",
            "SKIPS",
            f"{TraderWindow._skip_summary(diagnostics)}",
            "",
            "TIMING",
        ]

        timing = diagnostics.get("timings_seconds") or {}
        if isinstance(timing, dict):
            labels = (
                ("universe", "Universe"),
                ("benchmark", "Benchmark"),
                ("benchmark_d1", "Benchmark D1"),
                ("m5", "M5"),
                ("d1", "D1"),
                ("calculation", "Calculation"),
                ("total", "Total"),
            )
            for key, label in labels:
                if key in timing:
                    try:
                        lines.append(f"{label} {float(timing[key]):.3f}s")
                    except (TypeError, ValueError):
                        lines.append(f"{label} {timing[key]}")
        return "\n".join(lines)

    def copy_active_table(self):
        widget = self.market_tabs.currentWidget()
        if widget is self.result_stack:
            copied = self.spot_tabs.currentWidget().copy_selection()
        elif widget is getattr(self, "oi_panel", None):
            copied = getattr(self, "copy_oi_table", lambda: False)()
        elif widget is getattr(self, "diagnostics_panel", None):
            QApplication.clipboard().setText(self.diagnostics_box.toPlainText())
            copied = True
        else:
            table = widget.findChild(MarketTableWidget) if widget is not None else None
            copied = table.copy_selection() if table is not None else False
        if copied is False:
            self.copy_button.setText("NOTHING TO COPY")
        else:
            self.copy_button.setText("COPIED ✓")
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

    def _scan_failed(self, error):
        self.scan_button.setEnabled(True)
        self._stop_scan_animation()
        self.result_table.hide()
        self.weak_result_table.hide()
        self.result_box.setPlainText(f"SCAN ERROR\n\n{error}")
        self.diagnostics_box.setPlainText(f"SPOT SCAN ERROR\n\n{error}")

    def _scan_thread_finished(self):
        if self.scan_thread is not None:
            self.scan_thread.deleteLater()
        self.scan_thread = None
        self.scan_worker = None
