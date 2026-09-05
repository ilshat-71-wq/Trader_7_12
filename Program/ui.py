"""Trader_7_12 Pro — compact read-only market-information radar UI."""

from html import escape
import math

from PySide6.QtCore import QPointF, QThread, QTimer, Qt, QObject, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QLabel, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget

from services.market_attention_scanner_service import MarketAttentionScannerService
from services.market_session_service import MarketSessionService

ROLE_LABELS = {
    "LONG_CANDIDATE": "ЛИДЕР РЫНКА",
    "SHORT_CANDIDATE": "АУТСАЙДЕР РЫНКА",
    "MARKET_LEADER": "ЛИДЕР РЫНКА",
    "MARKET_LAGGARD": "АУТСАЙДЕР РЫНКА",
    "ATTENTION_WATCH": "ВЫСОКИЙ ТЕКУЩИЙ ИНТЕРЕС",
}
RS_LABELS = {"STRONGER": "СИЛЬНЕЕ РЫНКА", "WEAKER": "СЛАБЕЕ РЫНКА", "NEUTRAL": "НЕЙТРАЛЬНО", "UNAVAILABLE": "RS НЕДОСТУПЕН"}
SESSION_LABELS = {"PRE_OPEN": "ПРЕ-ОТКРЫТИЕ", "MORNING": "УТРЕННЯЯ СЕССИЯ", "MAIN": "ОСНОВНАЯ СЕССИЯ", "EVENING": "ВЕЧЕРНЯЯ СЕССИЯ", "WEEKEND_SESSION": "ДСВД", "CLOSED": "РЫНОК ЗАКРЫТ"}
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


def _role(item):
    return ROLE_LABELS.get(str(item.get("selection_role") or "").upper(), "—")


def _daily_label(item):
    structure = str(item.get("daily_structure_state") or "UNKNOWN")
    relation = str(item.get("daily_relative_direction") or "UNAVAILABLE")
    return f"{structure} / {relation}"


def _rs_label(item):
    relation = str(item.get("market_relation") or "").upper()
    if relation == "СИЛЬНЕЕ РЫНКА":
        return RS_LABELS["STRONGER"]
    if relation == "СЛАБЕЕ РЫНКА":
        return RS_LABELS["WEAKER"]
    return RS_LABELS["NEUTRAL"]


class MeltingClocksWidget(QWidget):
    """Animated scan-state visual."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.setMinimumHeight(420)

    def start(self):
        self.phase = 0.0
        self.timer.start(45)
        self.update()

    def stop(self):
        self.timer.stop()

    def _tick(self):
        self.phase += 0.075
        self.update()

    def _draw_clock(self, p, x, y, r, melt, angle):
        p.save(); p.translate(x, y)
        halo = QRadialGradient(0, 0, r * 1.35); halo.setColorAt(0, QColor(205, 218, 154, 30)); halo.setColorAt(1, QColor(205, 218, 154, 0))
        p.setPen(Qt.NoPen); p.setBrush(halo); p.drawEllipse(QPointF(0, 0), r * 1.35, r * 1.35)
        face = QRadialGradient(-r * .25, -r * .3, r * 1.15); face.setColorAt(0, QColor("#f1e7c8")); face.setColorAt(.72, QColor("#d8c99f")); face.setColorAt(1, QColor("#a99972"))
        p.setBrush(face); p.setPen(QPen(QColor("#806f4d"), max(2, r * .045))); p.drawEllipse(QPointF(0, 0), r, r)
        melt_gradient = QLinearGradient(0, r * .5, 0, r * 1.6); melt_gradient.setColorAt(0, QColor("#d8c99f")); melt_gradient.setColorAt(1, QColor("#9d8b62"))
        p.setBrush(melt_gradient); p.setPen(Qt.NoPen); p.drawRoundedRect(-r * .42, r * .58, r * .84, r * .48 + max(0, melt) * r, r * .18, r * .18)
        p.setPen(QPen(QColor("#6c6046"), max(1, r * .025)))
        for i in range(12):
            a = math.radians(i * 30 - 90); p.drawLine(QPointF(math.cos(a) * r * .78, math.sin(a) * r * .78), QPointF(math.cos(a) * r * .88, math.sin(a) * r * .88))
        a = math.radians(angle); p.setPen(QPen(QColor("#3e392d"), max(2, r * .035), Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(0, 0), QPointF(math.cos(a) * r * .58, math.sin(a) * r * .58))
        a2 = math.radians(angle * 12); p.setPen(QPen(QColor("#514a3a"), max(1.5, r * .025), Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(0, 0), QPointF(math.cos(a2) * r * .73, math.sin(a2) * r * .73))
        p.setBrush(QColor("#514a3a")); p.setPen(Qt.NoPen); p.drawEllipse(QPointF(0, 0), r * .06, r * .06); p.restore()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); rect = self.rect()
        bg = QLinearGradient(0, 0, 0, rect.height()); bg.setColorAt(0, QColor("#11161b")); bg.setColorAt(.55, QColor("#171c21")); bg.setColorAt(1, QColor("#0f1418")); p.fillRect(rect, bg)
        sweep = (math.sin(self.phase * .55) + 1) / 2; x = rect.left() + sweep * rect.width()
        band = QLinearGradient(x - 150, 0, x + 150, 0); band.setColorAt(0, QColor(190, 214, 120, 0)); band.setColorAt(.5, QColor(190, 214, 120, 22)); band.setColorAt(1, QColor(190, 214, 120, 0)); p.fillRect(rect, band)
        w, h = rect.width(), rect.height(); bob = math.sin(self.phase) * 7; sway = math.sin(self.phase * .7) * 9; base = min(w, h)
        self._draw_clock(p, w * .27 + sway, h * .48 + bob, base * .105, .30 + .08 * math.sin(self.phase * 1.4), -55 + self.phase * 18)
        self._draw_clock(p, w * .52 - sway * .35, h * .44 - bob * .5, base * .145, .55 + .12 * math.sin(self.phase * 1.15 + 1), 25 + self.phase * 14)
        self._draw_clock(p, w * .76 + sway * .45, h * .50 + bob * .8, base * .09, .38 + .09 * math.sin(self.phase * 1.25 + 2), 95 + self.phase * 20)
        p.setPen(QColor("#aab57d")); p.setFont(QFont("Helvetica Neue", 12, QFont.Weight.Medium)); p.drawText(rect.adjusted(0, 0, 0, -22), Qt.AlignHCenter | Qt.AlignBottom, "АНАЛИЗ SPOT-РЫНКА")
        p.setPen(QColor("#727b68")); p.setFont(QFont("Helvetica Neue", 10)); p.drawText(rect.adjusted(0, 0, 0, -7), Qt.AlignHCenter | Qt.AlignBottom, "D1  •  ЛИКВИДНОСТЬ  •  RS  •  ПОТОК"); p.end()


class MarketScanWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)
    def __init__(self, scanner, limit=3):
        super().__init__(); self.scanner = scanner; self.limit = limit
    def run(self):
        try:
            results = self.scanner.scan(limit=self.limit)
            self.finished.emit(results, getattr(self.scanner, "_last_scan_diagnostics", {}))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class TraderWindow(QWidget):
    """Read-only D1-led SPOT market-information radar."""
    def __init__(self, scanner_enabled=True):
        super().__init__(); self.setWindowTitle("Trader_7_12 Pro — Market Information Radar"); self.resize(1120, 780)
        self.scanner = MarketAttentionScannerService() if scanner_enabled else None; self.scanner_enabled = scanner_enabled
        self.scan_thread = None; self.scan_worker = None; self.session_service = MarketSessionService(); self.animation_step = 0
        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self._update_session_header)
        self.scan_animation_timer = QTimer(self); self.scan_animation_timer.timeout.connect(self._animate_scan)
        self.init_ui(); self.clock_timer.start(1000); self._update_session_header()

    def init_ui(self):
        self.setStyleSheet("""QWidget { background:#20252b; color:#e6e9ed; font-family:'Helvetica Neue',Arial,sans-serif; } QLabel { color:#e6e9ed; } QPushButton { background:#30373f; color:#f0f2f4; border:1px solid #46505a; border-radius:8px; padding:10px 18px; } QPushButton:hover { background:#38414a; } QPushButton:disabled { background:#30372e; border:1px solid #59634a; } QTextEdit { background:#171b20; color:#dfe3e7; border:1px solid #394149; border-radius:8px; padding:14px; }""")
        self.title = QLabel("TRADER_7_12 PRO"); self.title.setAlignment(Qt.AlignCenter); self.title.setStyleSheet("font-size:29px;font-weight:800;letter-spacing:1px;padding:8px")
        self.subtitle = QLabel("D1 • ЛИДЕРЫ / АУТСАЙДЕРЫ • MONEY FLOW • RS • READ-ONLY"); self.subtitle.setAlignment(Qt.AlignCenter); self.subtitle.setStyleSheet("font-size:13px;color:#89939d;padding:1px")
        self.session_label = QLabel(); self.session_label.setAlignment(Qt.AlignCenter); self.session_label.setStyleSheet("font-size:20px;font-weight:700;color:#cbd1d7;padding:4px")
        self.clock_label = QLabel(); self.clock_label.setAlignment(Qt.AlignCenter); self.clock_label.setStyleSheet("font-size:14px;color:#9fa8b1;padding-bottom:4px")
        self.scan_button = QPushButton("●  СКАНИРОВАТЬ РЫНОК"); self.scan_button.setMinimumHeight(54); self.scan_button.clicked.connect(self.run_market_scan); self._set_scan_button_style()
        self.result_box = QTextEdit(); self.result_box.setReadOnly(True); self.result_box.setStyleSheet("font-size:15px")
        self.scan_visual = MeltingClocksWidget(); self.result_stack = QStackedWidget(); self.result_stack.addWidget(self.result_box); self.result_stack.addWidget(self.scan_visual); self.result_stack.setCurrentWidget(self.result_box)
        self.result_box.setText("БКС ПОДКЛЮЧЁН\n\nНажмите «СКАНИРОВАТЬ РЫНОК».\nСканер сначала проверит завершённый D1, затем сегодняшний поток и RS.") if self.scanner_enabled else self.result_box.setText("РЕЖИМ ПРОСМОТРА\n\nБКС временно недоступен.")
        self.scan_button.setEnabled(self.scanner_enabled)
        layout = QVBoxLayout(); layout.setContentsMargins(18, 14, 18, 18); layout.setSpacing(6)
        for widget in (self.title, self.subtitle, self.session_label, self.clock_label, self.scan_button, self.result_stack): layout.addWidget(widget)
        self.setLayout(layout)

    def _set_scan_button_style(self, color=NEUTRAL_COLOR):
        self.scan_button.setStyleSheet(f"font-size:18px;font-weight:700;color:{color};background:#30373f;border:1px solid #46505a;border-radius:8px;padding:10px 18px")

    def _update_session_header(self):
        info = self.session_service.get_session_info(); session = info.get("session", "CLOSED")
        self.session_label.setText(SESSION_LABELS.get(session, session)); state = "РЫНОК ОТКРЫТ" if info.get("market_open") else "РЫНОК ЗАКРЫТ"
        self.clock_label.setText(f"{info.get('date','—')}  •  МСК {info.get('time','—')}  •  {state}")

    def _animate_scan(self):
        self.animation_step = (self.animation_step + 1) % len(SCAN_COLORS); self.scan_button.setText("●  ИДЁТ АНАЛИЗ D1 + M5"); self._set_scan_button_style(SCAN_COLORS[self.animation_step])

    def _start_scan_animation(self):
        self.scan_visual.start(); self.result_stack.setCurrentWidget(self.scan_visual); self.scan_animation_timer.start(260); self._animate_scan()

    def _stop_scan_animation(self):
        self.scan_animation_timer.stop(); self.scan_visual.stop(); self.scan_button.setText("●  СКАНИРОВАТЬ РЫНОК"); self._set_scan_button_style(); self.result_stack.setCurrentWidget(self.result_box)

    def run_market_scan(self):
        if not self.scanner_enabled or (self.scan_thread is not None and self.scan_thread.isRunning()): return
        self.scan_button.setEnabled(False); self._start_scan_animation()
        try:
            self.scan_thread = QThread(self); self.scan_worker = MarketScanWorker(self.scanner, limit=3); self.scan_worker.moveToThread(self.scan_thread)
            self.scan_thread.started.connect(self.scan_worker.run); self.scan_worker.finished.connect(self._scan_finished); self.scan_worker.failed.connect(self._scan_failed)
            self.scan_worker.finished.connect(self.scan_thread.quit); self.scan_worker.failed.connect(self.scan_thread.quit); self.scan_thread.finished.connect(self._scan_thread_finished); self.scan_thread.start()
        except Exception as exc: self._scan_failed(f"{type(exc).__name__}: {exc}")

    def _scan_finished(self, results, diagnostics):
        self.scan_button.setEnabled(True); self._stop_scan_animation(); info = self.session_service.get_session_info(); session_name = SESSION_LABELS.get(info.get("session", "CLOSED"), "РЫНОК")
        lines = ["<pre style='font-family:Menlo,Monaco,monospace;font-size:14px;color:#dfe3e7'>", "═" * 82,
                 "TRADER_7_12 PRO — D1 + RS + FLOW", "═" * 82, "", f"{session_name} • {info.get('date','—')} • МСК {info.get('time','—')}", "",
                 f"СТАТУС: {escape(str(diagnostics.get('status') or '—'))}",
                 f"ПОКРЫТИЕ: {_number(diagnostics.get('coverage_percent'), 1)}% / требуется {_number(diagnostics.get('coverage_required_percent'), 1)}%",
                 f"АНАЛИЗИРОВАНО: {diagnostics.get('analyzed', 0)} / {diagnostics.get('universe_total', 0)}",
                 f"BENCHMARK: {escape(str(diagnostics.get('benchmark') or '—'))}  •  D1: {diagnostics.get('daily_benchmark_days', 0)} свечей", ""]
        if not results:
            lines += ["КВАЛИФИЦИРОВАННЫХ ЛИДЕРОВ / АУТСАЙДЕРОВ НЕТ", "", "Информационный критерий не выполнен: обязательные D1/RS/flow-проверки не дали результата."]
        else:
            for idx, item in enumerate(results, 1):
                lines += ["", f"████  #{idx}  {escape(str(item.get('spot_ticker') or '—'))}  ████",
                          f"КЛАССИФИКАЦИЯ:     {_role(item)}",
                          f"D1:                  {_daily_label(item)}", f"D1 RS:               {_number(item.get('daily_relative_mean_pp'), 3)} п.п.",
                          f"ТЕКУЩИЙ RS:          {_number(item.get('relative_strength'), 3)} п.п.  •  {_rs_label(item)}",
                          f"RS SCORE:            {_number(item.get('relative_strength_score'), 1)} / 100", f"INFORMATION SCORE:   {_number(item.get('directional_score'), 1)} / 100",
                          f"ЦЕНА:                {_number(item.get('price'), 4)}", f"ИЗМЕНЕНИЕ:           {_number(item.get('change_percent'), 2)}%",
                          f"СЕССИЯ ₽×V:          {_money(item.get('session_money'))}", f"₽×V / МИН:            {_money(item.get('money_per_minute'))}",
                          f"ПОСЛЕДНИЕ 15 МИН:    {_money(item.get('recent_money'))}", f"УСКОРЕНИЕ FLOW:      {_number(item.get('money_acceleration'), 1)}%", "─" * 82]
        lines += ["", "READ-ONLY: программа только показывает рыночные данные и классификации.", "═" * 82, "</pre>"]
        self.result_box.setHtml("\n".join(lines))

    def _scan_failed(self, error):
        self.scan_button.setEnabled(True); self._stop_scan_animation(); self.result_box.setText(f"ОШИБКА СКАНИРОВАНИЯ\n\n{error}")

    def _scan_thread_finished(self):
        if self.scan_thread is not None: self.scan_thread.deleteLater()
        self.scan_thread = None; self.scan_worker = None
