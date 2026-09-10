"""Trader_7_12 Pro — single-window OI-enabled dashboard."""

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from ui import TraderWindow
from ui_table import MarketTableWidget, numeric
from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.market_information_scanner_service import MarketInformationScannerService


class FuturesOIWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        try:
            results, diagnostics = self.service.scan()
            self.finished.emit(results, diagnostics)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class OIWatchlistTraderWindow(TraderWindow):
    """Single Trader_7_12 Pro window: SPOT market map + Futures OI context."""

    VERSION = "2.7.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        if scanner_enabled:
            self.scanner = MarketInformationScannerService()
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.resize(1280, 980)
        self.setMinimumSize(1120, 900)
        self.subtitle.setText("D1 • MARKET MAP • MONEY FLOW • RS • FUTURES OI LIQUIDITY TOP • READ-ONLY")

        self.oi_meta = QLabel()
        self.oi_meta.setWordWrap(True)
        self.oi_meta.setStyleSheet("background:#171b20;color:#b9c1c8;border:1px solid #394149;border-radius:8px;padding:10px 14px;font-size:12px")
        self.oi_table = MarketTableWidget(
            ["#", "Root", "Contract", "Base", "FUT Δ%", "BASE Δ%", "OI", "ΔOI%", "DAY ₽", "Mode"],
            [42, 68, 122, 76, 78, 82, 110, 78, 104, 190],
        )
        self.oi_panel = QWidget()
        oi_layout = QVBoxLayout(self.oi_panel)
        oi_layout.setContentsMargins(0, 0, 0, 0)
        oi_layout.setSpacing(6)
        oi_layout.addWidget(self.oi_meta)
        oi_layout.addWidget(self.oi_table, 1)

        self.market_tabs = QTabWidget()
        self.market_tabs.setDocumentMode(True)
        self.layout().removeWidget(self.result_stack)
        self.market_tabs.addTab(self.result_stack, "SPOT • MARKET MAP")
        self.market_tabs.addTab(self.oi_panel, "FUTURES OI • CONTEXT")
        self.layout().addWidget(self.market_tabs, 1)

        self.oi_thread = None
        self.oi_worker = None
        self.oi_meta.setText(
            "FUTURES OI — LIQUIDITY TOP 20\n\nПосле сканирования SPOT здесь автоматически появятся наиболее ликвидные front-контракты с реальным денежным оборотом текущего торгового дня."
            if scanner_enabled else "FUTURES OI\n\nBCS временно недоступен."
        )
        self.oi_table.hide()

    def _scan_finished(self, results, diagnostics):
        super()._scan_finished(results, diagnostics)
        if self.scanner_enabled:
            self._start_oi_scan()

    def _start_oi_scan(self):
        if self.oi_thread is not None and self.oi_thread.isRunning():
            return
        self.oi_meta.setText("FUTURES OI — LIQUIDITY TOP 20\n\nИдёт загрузка front-контрактов, MOEX OI и оборота текущего торгового дня…")
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
            if value >= 1_000_000_000:
                return f"{value / 1_000_000_000:.2f} млрд"
            if value >= 1_000_000:
                return f"{value / 1_000_000:.2f} млн"
            if value >= 1_000:
                return f"{value / 1_000:.1f} тыс"
            return f"{value:.0f}"
        except (TypeError, ValueError):
            return "—"

    def _oi_finished(self, results, diagnostics):
        self.oi_meta.setText(
            f"FUTURES OI — LIQUIDITY TOP 20   •   СТАТУС: {diagnostics.get('status') or '—'}   •   "
            f"TOP: {diagnostics.get('liquidity_top_returned', len(results))}   •   "
            f"OI AVAILABLE: {diagnostics.get('oi_available', 0)}   •   "
            f"LIQUIDITY WITH MONEY: {diagnostics.get('liquidity_available', 0)}\n"
            f"FRONT FAMILIES: {diagnostics.get('contracts', 0)}   •   FULL OI ANALYSIS: {diagnostics.get('analyzed', 0)}   •   "
            f"TURNOVER: {diagnostics.get('liquidity_metric') or '—'}   •   SOURCE: VALTODAY"
        )
        rows = []
        for item in results or []:
            oi = item.get("oi_analysis") or {}
            rank = int(item.get("liquidity_rank") or 0)
            rows.append([
                numeric(rank), str(item.get("oi_root") or item.get("futures_root") or "—"),
                str(item.get("futures_ticker") or "—"), str(item.get("underlying_asset") or "—"),
                numeric(self._signed(item.get("change_percent"), 2)),
                numeric(self._signed(item.get("underlying_change_percent"), 2)),
                numeric(self._fmt(oi.get("oi"), 0)),
                numeric(self._signed(oi.get("oi_change_percent"), 2)),
                numeric(self._money(item.get("session_turnover_rub"))),
                str(oi.get("oi_regime", "—")),
            ])
        self.oi_table.set_rows(rows)
        self.oi_table.setToolTip("DAY ₽ = реальный VALTODAY, накопленный с начала текущего торгового дня. Порядок строк = реальная ликвидность. UI не изменяет расчёты.")
        self.oi_table.setVisible(bool(rows))
        if not rows:
            self.oi_meta.setText(self.oi_meta.text() + "\n\nНет доступных front-контрактов с ненулевым OI и реальным оборотом.")

    def _oi_failed(self, error):
        self.oi_table.hide()
        self.oi_meta.setText(f"FUTURES OI\n\nОшибка OI-аналитики: {error}")

    def _oi_thread_finished(self):
        if self.oi_thread is not None:
            self.oi_thread.deleteLater()
        self.oi_thread = None
        self.oi_worker = None
