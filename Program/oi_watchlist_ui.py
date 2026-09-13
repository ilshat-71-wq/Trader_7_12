"""Trader_7_12 Pro — single-window dashboard with Futures OI + money flow."""

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import TraderWindow
from ui_table import MarketTableWidget, numeric
from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.money_flow_service import MoneyFlowService


class FuturesOIWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.money_flow = MoneyFlowService()

    def run(self):
        try:
            results, diagnostics = self.service.scan()
            results = self.money_flow.analyze(results, api=self.service.api)
            diagnostics = dict(diagnostics or {})
            available = [r for r in results if r.get("money_flow_status") == "AVAILABLE"]
            hot = [r for r in available if r.get("money_flow_liquidity_state") == "HOT"]
            diagnostics.update({
                "money_flow_status": "AVAILABLE" if available else "NO_DATA",
                "money_flow_available": len(available),
                "money_flow_hot_liquidity": len(hot),
                "money_flow_top_ranked": min(5, len(available)),
                "money_flow_window_minutes": MoneyFlowService.WINDOW_MINUTES,
                "money_flow_liquidity_window_minutes": MoneyFlowService.LIQUIDITY_WINDOW_MINUTES,
                "money_flow_source": "BCS_LAST_TRADES_30M_PLUS_CURRENT_ORDER_BOOK",
                "money_flow_policy": "REAL_BCS_DATA_ONLY; NO_PARTICIPANT_IDENTITY_CLAIM",
            })
            self.finished.emit(results, diagnostics)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class OIWatchlistTraderWindow(TraderWindow):
    """One professional read-only window: SPOT radar + Futures OI + money flow."""

    VERSION = "2.9.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.oi_thread = None
        self.oi_worker = None
        self._oi_diagnostics = {}
        self.oi_panel = self._build_oi_panel()
        self.market_tabs.addTab(self.oi_panel, "FUTURES OI")
        self.market_tabs.tabBar().moveTab(2, 1)
        self.oi_meta.setText(
            "После сканирования появятся front-контракты с реальным OI/VALTODAY "
            "и анализом реального денежного потока BCS."
            if scanner_enabled else "BCS временно недоступен."
        )
        self.oi_table.hide()

    def _build_oi_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)
        self.oi_meta = QLabel()
        self.oi_meta.setWordWrap(True)
        self.oi_meta.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.oi_meta.setStyleSheet(
            "background:#171b20;color:#b9c1c8;border:1px solid #394149;"
            "border-radius:8px;padding:9px 12px;font-size:11px;"
        )
        layout.addWidget(self.oi_meta)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        hint = QLabel(
            "🟢 LIQUIDITY NOW = максимальный реальный денежный поток за последние 5 мин • "
            "FLOW = направление • ACTION = вероятное состояние позиции по цене + OI • ZONE = зона потока"
        )
        hint.setStyleSheet("color:#7f8a94;font-size:10px;padding-left:3px;")
        toolbar.addWidget(hint, 1)
        self.oi_copy_button = QPushButton("КОПИРОВАТЬ OI")
        self.oi_copy_button.clicked.connect(self.copy_oi_table)
        toolbar.addWidget(self.oi_copy_button)
        layout.addLayout(toolbar)
        self.oi_table = MarketTableWidget(
            ["#", "Root", "Contract", "Base", "FUT Δ%", "BASE Δ%", "OI", "ΔOI%", "DAY ₽", "LIQ NOW", "FLOW", "ACTION", "ZONE"],
            [42, 58, 122, 100, 72, 82, 105, 78, 105, 92, 150, 145, 150],
        )
        layout.addWidget(self.oi_table, 1)
        return panel

    def _scan_finished(self, results, diagnostics):
        super()._scan_finished(results, diagnostics)
        if self.scanner_enabled:
            self._start_oi_scan()

    def _start_oi_scan(self):
        if self.oi_thread is not None and self.oi_thread.isRunning():
            return
        self.oi_meta.setText("ЗАГРУЗКА FUTURES OI • реальный VALTODAY • Last Trades 30m • Liquidity Now 5m • текущий Order Book…")
        self.oi_table.hide()
        self.oi_thread = QThread(self)
        self.oi_worker = FuturesOIWorker(FuturesOIMarketDataScannerService())
        self.oi_worker.moveToThread(self.oi_thread)
        self.oi_thread.started.connect(self.oi_worker.run)
        self.oi_worker.finished.connect(self._oi_finished)
        self.oi_worker.failed.connect(self._oi_failed)
        self.oi_worker.finished.connect(self.oi_thread.quit)
        self.oi_worker.failed.connect(self.oi_thread.quit)
        self.oi_thread.finished.connect(self._oi_thread_finished)
        self.oi_thread.start()

    @staticmethod
    def _fmt(value, digits=2):
        try:
            return f"{float(value):,.{digits}f}".replace(",", " ")
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _signed(value, digits=2):
        try:
            return f"{float(value):+,.{digits}f}".replace(",", " ")
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _money(value):
        try:
            value = float(value)
            if value >= 1_000_000_000: return f"{value / 1_000_000_000:.2f} млрд"
            if value >= 1_000_000: return f"{value / 1_000_000:.2f} млн"
            if value >= 1_000: return f"{value / 1_000:.1f} тыс"
            return f"{value:.0f}"
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _flow_text(item):
        signal = item.get("money_flow_signal") or "NO_DATA"
        delta = item.get("money_flow_delta_pct")
        confidence = item.get("money_flow_confidence") or "LOW"
        if delta is None: return "—"
        return f"{signal} {float(delta):+.1f}% / {confidence}"

    @staticmethod
    def _liquidity_text(item):
        score = item.get("money_flow_liquidity_score")
        total = item.get("money_flow_recent_total")
        direction = item.get("money_flow_liquidity_direction") or "NO_DATA"
        state = item.get("money_flow_liquidity_state") or "NO_DATA"
        if score is None or not total: return "—"
        return f"{state} {float(score):.0f} • {direction} • {OIWatchlistTraderWindow._money(total)}"

    @staticmethod
    def _action_text(item):
        action = item.get("money_flow_position_action") or "—"
        confidence = item.get("money_flow_position_confidence") or "LOW"
        return f"{action} / {confidence}"

    @staticmethod
    def _zone_text(item):
        low = item.get("money_flow_zone_low")
        high = item.get("money_flow_zone_high")
        vwap = item.get("money_flow_zone_vwap")
        if low is None or high is None: return "—"
        if abs(float(high) - float(low)) < 1e-12:
            return f"{float(low):.4f}"
        suffix = f" • VWAP {float(vwap):.4f}" if vwap is not None else ""
        return f"{float(low):.4f}–{float(high):.4f}{suffix}"

    def _highlight_money_rows(self, results):
        for row, item in enumerate(results):
            rank = item.get("money_flow_rank")
            liquidity = str(item.get("money_flow_liquidity_state") or "")
            signal = str(item.get("money_flow_signal") or "")
            action = str(item.get("money_flow_position_action") or "")
            confidence = str(item.get("money_flow_confidence") or "")
            if liquidity == "HOT":
                brush = QBrush(QColor("#123f2a"))
            elif rank is not None and int(rank) <= 5:
                brush = QBrush(QColor("#163b2f"))
            else:
                brush = None
            if brush:
                for col in range(self.oi_table.columnCount()):
                    cell = self.oi_table.item(row, col)
                    if cell: cell.setBackground(brush)
            if signal in {"ACCUMULATION", "BUY_ABSORPTION", "BUYER_ACTIVE"}:
                cell = self.oi_table.item(row, 10)
                if cell: cell.setForeground(QBrush(QColor("#69e59a")))
            elif signal in {"DISTRIBUTION", "SELL_ABSORPTION", "SELLER_ACTIVE"}:
                cell = self.oi_table.item(row, 10)
                if cell: cell.setForeground(QBrush(QColor("#ff7d7d")))
            if action in {"LONG_BUILDUP", "SHORT_COVERING"}:
                cell = self.oi_table.item(row, 11)
                if cell: cell.setForeground(QBrush(QColor("#69e59a")))
            elif action in {"SHORT_BUILDUP", "LONG_LIQUIDATION"}:
                cell = self.oi_table.item(row, 11)
                if cell: cell.setForeground(QBrush(QColor("#ff7d7d")))
            if confidence == "HIGH":
                cell = self.oi_table.item(row, 11)
                if cell: cell.setFont(cell.font())

    def _oi_finished(self, results, diagnostics):
        self._oi_diagnostics = diagnostics or {}
        self.oi_meta.setText(
            f"FUTURES OI • STATUS {diagnostics.get('status') or '—'} • "
            f"TOP {diagnostics.get('liquidity_top_returned', len(results))} • "
            f"OI {diagnostics.get('oi_available', 0)} • "
            f"HOT LIQUIDITY {diagnostics.get('money_flow_hot_liquidity', 0)}\n"
            f"DAY ₽ = VALTODAY • LIQ NOW = Last Trades 5m • FLOW = Last Trades 30m + текущий стакан • "
            f"ACTION = вероятная структура позиции по цене + ΔOI • 🟢 = максимальная текущая активность"
        )
        rows = []
        for index, item in enumerate(results or [], 1):
            oi = item.get("oi_analysis") or {}
            rows.append([
                numeric(item.get("money_flow_rank") or index),
                str(item.get("oi_root") or item.get("futures_root") or "—"),
                str(item.get("futures_ticker") or "—"),
                str(item.get("underlying_ticker") or "—"),
                numeric(self._signed(item.get("change_percent"), 2)),
                numeric(self._signed(item.get("underlying_change_pct"), 2)),
                numeric(self._fmt(oi.get("oi"), 0)),
                numeric(self._signed(oi.get("oi_change_percent"), 2)),
                numeric(self._money(item.get("turnover_rub"))),
                self._liquidity_text(item),
                self._flow_text(item),
                self._action_text(item),
                self._zone_text(item),
            ])
        self.oi_table.set_rows(rows)
        self._highlight_money_rows(results or [])
        self.oi_table.setToolTip(
            "LIQ NOW — реальная денежная активность обезличенных сделок BCS за последние 5 минут. "
            "FLOW — наблюдаемое направление потока за 30 минут с учётом текущего стакана. "
            "ACTION — вероятная структура позиции по направлению цены и изменению OI; это не идентификация участника. "
            "ZONE — ценовой диапазон доминирующего потока и его VWAP. DAY ₽ = реальный VALTODAY."
        )
        self.oi_table.setVisible(bool(rows))
        if not rows:
            self.oi_meta.setText(self.oi_meta.text() + "\nНет доступных данных.")
        self._append_oi_diagnostics()

    def _append_oi_diagnostics(self):
        base = self.diagnostics_box.toPlainText().rstrip()
        lines = ["", "", "=== FUTURES OI / REAL MONEY FLOW ==="]
        for key, value in self._oi_diagnostics.items():
            lines.append(f"{key}: {value}")
        self.diagnostics_box.setPlainText(base + "\n" + "\n".join(lines))

    def copy_oi_table(self):
        self.oi_table.copy_selection()
        self.market_tabs.setCurrentWidget(self.oi_panel)

    def _oi_failed(self, error):
        self.oi_table.hide()
        self._oi_diagnostics = {"error": error}
        self.oi_meta.setText(f"FUTURES OI\n\nОшибка OI-аналитики: {error}")
        self._append_oi_diagnostics()

    def _oi_thread_finished(self):
        if self.oi_thread is not None:
            self.oi_thread.deleteLater()
        self.oi_thread = None
        self.oi_worker = None
