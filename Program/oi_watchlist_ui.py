"""Trader_7_12 Pro — single-window OI-enabled dashboard."""

from html import escape

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QTextEdit

from ui import TraderWindow
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
    """The single Trader_7_12 Pro window: SPOT radar + Futures OI Liquidity TOP."""

    VERSION = "2.7.0"

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        if scanner_enabled:
            self.scanner = MarketInformationScannerService()
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.resize(1280, 980)
        self.setMinimumSize(1120, 900)
        self.subtitle.setText("D1 • ЛИДЕРЫ / АУТСАЙДЕРЫ • MONEY FLOW • RS • FUTURES OI LIQUIDITY TOP • READ-ONLY")

        self.oi_box = QTextEdit()
        self.oi_box.setReadOnly(True)
        self.oi_box.setMinimumHeight(340)
        self.oi_box.setMaximumHeight(420)
        self.oi_box.setStyleSheet("font-size:13px")
        self.layout().addWidget(self.oi_box)

        self.oi_thread = None
        self.oi_worker = None
        self.oi_box.setText(
            "FUTURES OI — LIQUIDITY TOP 20\n\n"
            "После сканирования SPOT здесь автоматически появятся только\n"
            "наиболее ликвидные front-контракты, где есть реальные деньги\n"
            "в текущей торговой сессии: FUT Δ → BASE Δ → OI → ΔOI → Оборот ₽ → режим."
            if scanner_enabled else "FUTURES OI\n\nBCS временно недоступен."
        )

    def _scan_finished(self, results, diagnostics):
        super()._scan_finished(results, diagnostics)
        if self.scanner_enabled:
            self._start_oi_scan()

    def _start_oi_scan(self):
        if self.oi_thread is not None and self.oi_thread.isRunning():
            return
        self.oi_box.setText("FUTURES OI — LIQUIDITY TOP 20\n\nИдёт загрузка front-контрактов, MOEX OI и текущего оборота…")
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
        lines = [
            "FUTURES OI — LIQUIDITY TOP 20",
            "═" * 128,
            f"СТАТУС: {escape(str(diagnostics.get('status') or '—'))} • "
            f"TOP: {diagnostics.get('liquidity_top_returned', len(results))} • "
            f"OI AVAILABLE: {diagnostics.get('oi_available', 0)} • "
            f"LIQUIDITY WITH MONEY: {diagnostics.get('liquidity_available', 0)} • "
            f"ИСТОЧНИК OI: {escape(str(diagnostics.get('oi_source') or '—'))}",
            f"FRONT FAMILIES: {diagnostics.get('contracts', 0)} • FULL OI ANALYSIS: {diagnostics.get('analyzed', 0)} • "
            f"TURNOVER SOURCE: {escape(str(diagnostics.get('liquidity_metric') or '—'))}",
            "",
            "#  ROOT     CONTRACT           BASE         FUT Δ%    BASE Δ%        OI       ΔOI%    SESSION ₽×V       MODE",
            "─" * 128,
        ]
        if not results:
            lines.append("Нет ликвидных front-контрактов с текущим денежным оборотом.")
        else:
            for item in results:
                oi = item.get("oi_analysis") or {}
                rank = int(item.get("liquidity_rank") or 0)
                root = str(item.get("oi_root") or item.get("futures_root") or "—")
                contract = str(item.get("futures_ticker") or "—")
                base = str(item.get("underlying_asset") or "—")
                turnover = item.get("session_turnover_rub")
                lines.append(
                    f"{rank:>2}  {root:<8} {contract:<18} {base:<10} "
                    f"{self._signed(item.get('change_percent'), 2):>8} "
                    f"{self._signed(item.get('underlying_change_percent'), 2):>9} "
                    f"{self._fmt(oi.get('oi'), 0):>11} "
                    f"{self._signed(oi.get('oi_change_percent'), 2):>8} "
                    f"{self._money(turnover):>15}  {oi.get('oi_regime', '—')}"
                )
                lines.append(
                    f"    → liquidity #{rank} | money={self._money(turnover)} ₽ | "
                    f"OI strength={oi.get('oi_strength', '—')} | alignment={item.get('direction_alignment', '—')} | FRONT"
                )
        lines += [
            "",
            "LIQUIDITY TOP = front-контракты с OI>0, отсортированные по реальному денежному обороту текущей сессии.",
            "Синтетический PRICE × VOLUME для ранжирования не используется.",
            "OI: ↑цена+↑OI = набор вверх | ↑цена+↓OI = short covering | ↓цена+↑OI = набор вниз | ↓цена+↓OI = long liquidation.",
            "Остальной futures universe не потерян из источника: в основной таблице показывается только TOP ликвидности, чтобы убрать шум.",
            "OI — подтверждающий/контекстный слой. BUY/SELL и исполнение отсутствуют.",
        ]
        self.oi_box.setPlainText("\n".join(lines))

    def _oi_failed(self, error):
        self.oi_box.setText(f"FUTURES OI\n\nОшибка OI-аналитики: {error}")

    def _oi_thread_finished(self):
        if self.oi_thread is not None:
            self.oi_thread.deleteLater()
        self.oi_thread = None
        self.oi_worker = None
