"""Trader_7_12 Pro — single-window dashboard with Futures OI context."""

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import TraderWindow
from ui_table import MarketTableWidget, numeric
from services.futures_oi_marketdata_scanner_service import (
    FuturesOIMarketDataScannerService,
)


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
    """One professional read-only window: SPOT radar + Futures OI."""

    VERSION = "2.7.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)

        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.oi_thread = None
        self.oi_worker = None
        self._oi_diagnostics = {}

        self.oi_panel = self._build_oi_panel()
        self.market_tabs.addTab(self.oi_panel, "FUTURES OI")
        # Daily workflow: Radar → Futures OI → Diagnostics.
        self.market_tabs.tabBar().moveTab(2, 1)

        self.oi_meta.setText(
            "После сканирования SPOT здесь автоматически появятся front-контракты "
            "с реальным OI и реальным денежным оборотом MOEX RFUD."
            if scanner_enabled else
            "BCS временно недоступен."
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
            "OI + ΔOI + price/OI regime • DAY ₽ = VALTODAY • сортировка по заголовкам"
        )
        hint.setStyleSheet("color:#7f8a94;font-size:10px;padding-left:3px;")
        toolbar.addWidget(hint, 1)

        self.oi_copy_button = QPushButton("КОПИРОВАТЬ OI")
        self.oi_copy_button.clicked.connect(self.copy_oi_table)
        toolbar.addWidget(self.oi_copy_button)
        layout.addLayout(toolbar)

        self.oi_table = MarketTableWidget(
            ["#", "Root", "Contract", "Base", "FUT Δ%", "BASE Δ%",
             "OI", "ΔOI%", "DAY ₽", "Mode"],
            [42, 68, 122, 90, 78, 84, 112, 82, 112, 220],
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

        self.oi_meta.setText(
            "ЗАГРУЗКА FUTURES OI • front-контракты • MOEX RFUD • реальный VALTODAY…"
        )
        self.oi_table.hide()

        self.oi_thread = QThread(self)
        self.oi_worker = FuturesOIWorker(
            FuturesOIMarketDataScannerService()
        )
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
        self._oi_diagnostics = diagnostics or {}

        self.oi_meta.setText(
            f"FUTURES OI • STATUS {diagnostics.get('status') or '—'} • "
            f"TOP {diagnostics.get('liquidity_top_returned', len(results))} • "
            f"OI {diagnostics.get('oi_available', 0)} • "
            f"LIQUIDITY {diagnostics.get('liquidity_available', 0)}\n"
            f"FRONT {diagnostics.get('contracts', 0)} • "
            f"ANALYZED {diagnostics.get('analyzed', 0)} • "
            f"SOURCE {diagnostics.get('liquidity_metric') or 'VALTODAY'}"
        )

        rows = []
        for item in results or []:
            oi = item.get("oi_analysis") or {}
            rank = int(item.get("liquidity_rank") or 0)
            rows.append([
                numeric(rank),
                str(item.get("oi_root") or item.get("futures_root") or "—"),
                str(item.get("futures_ticker") or "—"),
                str(item.get("underlying_asset") or "—"),
                numeric(self._signed(item.get("change_percent"), 2)),
                numeric(self._signed(item.get("underlying_change_percent"), 2)),
                numeric(self._fmt(oi.get("oi"), 0)),
                numeric(self._signed(oi.get("oi_change_percent"), 2)),
                numeric(self._money(item.get("session_turnover_rub"))),
                str(oi.get("oi_regime", "—")),
            ])

        self.oi_table.set_rows(rows)
        self.oi_table.setToolTip(
            "DAY ₽ = реальный VALTODAY, накопленный с начала текущего "
            "торгового дня. Сортировка — по заголовкам. ⌘C / Ctrl+C — копирование."
        )
        self.oi_table.setVisible(bool(rows))

        if not rows:
            self.oi_meta.setText(
                self.oi_meta.text()
                + "\nНет доступных front-контрактов с ненулевым OI и реальным оборотом."
            )

        self._append_oi_diagnostics()

    def _append_oi_diagnostics(self):
        base = self.diagnostics_box.toPlainText().rstrip()
        lines = ["", "", "=== FUTURES OI / MOEX RFUD ==="]
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
