"""Trader_7_12 Pro — single-window dashboard with Futures OI + money flow."""

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import TraderWindow
from ui_table import MarketTableWidget, numeric
from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.money_flow_service import MoneyFlowService
from services.signal_probability_service import SignalProbabilityService
from services.realtime_microstructure_service import RealtimeMicrostructureWorker


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

    VERSION = "2.10.0"
    TURNOVER_HIGHLIGHT_TOP = 5

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.setWindowTitle("Trader_7_12 Pro — Market Information Radar")
        self.oi_thread = None
        self.oi_worker = None
        self._oi_diagnostics = {}
        self.signal_probability = SignalProbabilityService()
        self._oi_previous_probabilities = {}
        self.realtime_thread = None
        self.realtime_worker = None
        self._realtime_by_ticker = {}
        self.oi_panel = self._build_oi_panel()
        self.market_tabs.addTab(self.oi_panel, "FUTURES OI")
        self.market_tabs.tabBar().moveTab(2, 1)
        self.oi_meta.setText(
            "After scanning, front contracts with real OI/VALTODAY "
            "and real BCS money-flow analysis will appear here."
            if scanner_enabled else "BCS temporarily unavailable."
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
            "LIQ NOW = current BCS trade activity • FLOW = 30m real flow • "
            "BOOK/TAPE/FLOW RT = live BCS WebSocket • ACTION = price + OI structure • ZONE = VWAP / flow"
        )
        hint.setStyleSheet("color:#7f8a94;font-size:10px;padding-left:3px;")
        toolbar.addWidget(hint, 1)
        self.oi_copy_button = QPushButton("COPY")
        self.oi_copy_button.clicked.connect(self.copy_oi_table)
        toolbar.addWidget(self.oi_copy_button)
        layout.addLayout(toolbar)
        self.oi_table = MarketTableWidget(
            ["#", "Root", "Contract", "Base", "FUT Δ%", "OI", "ΔOI%", "DAY ₽", "LIQ NOW", "FLOW", "BOOK", "TAPE", "FLOW RT", "ACTION", "ZONE",
             "SIGNAL", "PROB", "ΔPROB"],
            [38, 55, 112, 92, 68, 92, 70, 94, 118, 125, 82, 82, 82, 130, 142, 78, 72, 72],
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
        self._stop_realtime()
        self.oi_meta.setText("LOADING • OI + VALTODAY • 5/30m money flow • order book…")
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
            if value >= 1_000_000_000: return f"{value / 1_000_000_000:.2f}B"
            if value >= 1_000_000: return f"{value / 1_000_000:.2f}M"
            if value >= 1_000: return f"{value / 1_000:.1f}K"
            return f"{value:.0f}"
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _flow_text(item):
        signal = str(item.get("money_flow_signal") or "NO_DATA")
        delta = item.get("money_flow_delta_pct")
        confidence = str(item.get("money_flow_confidence") or "LOW")
        if delta is None or signal == "NO_DATA":
            return "—"
        short = {
            "ACCUMULATION": "BUY",
            "BUY_ABSORPTION": "BUY ABS",
            "BUYER_ACTIVE": "BUY",
            "DISTRIBUTION": "SELL",
            "SELL_ABSORPTION": "SELL ABS",
            "SELLER_ACTIVE": "SELL",
        }.get(signal, signal)
        return f"{short} {float(delta):+.0f}% • {confidence[0]}"

    @staticmethod
    def _liquidity_text(item):
        score = item.get("money_flow_liquidity_score")
        total = item.get("money_flow_recent_total")
        direction = str(item.get("money_flow_liquidity_direction") or "")
        state = str(item.get("money_flow_liquidity_state") or "")
        if score is None or not total:
            return "—"
        mark = "●" if state == "HOT" else "○"
        direction_short = {"BUY": "B", "SELL": "S"}.get(direction, "—")
        return f"{mark} {float(score):.0f} • {direction_short} • {OIWatchlistTraderWindow._money(total)}"

    @staticmethod
    def _action_text(item):
        action = str(item.get("money_flow_position_action") or "—")
        confidence = str(item.get("money_flow_position_confidence") or "LOW")
        short = {
            "LONG_BUILDUP": "LONG ↑",
            "SHORT_BUILDUP": "SHORT ↓",
            "SHORT_COVERING": "COVER ↑",
            "LONG_LIQUIDATION": "LIQUIDATE ↓",
        }.get(action, action)
        if short == "—":
            return "—"
        return f"{short} • {confidence[0]}"

    @staticmethod
    def _zone_text(item):
        low = item.get("money_flow_zone_low")
        high = item.get("money_flow_zone_high")
        vwap = item.get("money_flow_zone_vwap")
        if low is None or high is None:
            return "—"
        if abs(float(high) - float(low)) < 1e-12:
            return f"{float(low):.4f}"
        suffix = f" / {float(vwap):.4f}" if vwap is not None else ""
        return f"{float(low):.4f}–{float(high):.4f}{suffix}"

    def _highlight_money_rows(self, results):
        # Green row highlight has one unambiguous meaning in OI:
        # top-5 futures by real current-day monetary turnover (VALTODAY),
        # i.e. the available exchange Price*Volume-style notional. We do not
        # replace it with the money-flow rank or HOT liquidity score.
        turnover_values = []
        for item in results:
            try:
                turnover = float(item.get("turnover_rub") or 0.0)
            except (TypeError, ValueError):
                turnover = 0.0
            turnover_values.append(turnover)
        top_turnovers = sorted(
            {value for value in turnover_values if value > 0},
            reverse=True,
        )[: self.TURNOVER_HIGHLIGHT_TOP]
        top_turnovers = set(top_turnovers)

        for row, item in enumerate(results):
            try:
                turnover = float(item.get("turnover_rub") or 0.0)
            except (TypeError, ValueError):
                turnover = 0.0

            if turnover > 0 and turnover in top_turnovers:
                brush = QBrush(QColor("#123f2a"))
                for col in range(self.oi_table.columnCount()):
                    cell = self.oi_table.item(row, col)
                    if cell:
                        cell.setBackground(brush)

            # FLOW/ACTION keep their analytical colors; they are independent
            # from the row-level monetary-turnover highlight.
            action = str(item.get("money_flow_position_action") or "")
            confidence = str(item.get("money_flow_position_confidence") or "")
            if confidence == "HIGH":
                cell = self.oi_table.item(row, 10)
                if cell:
                    font = QFont(cell.font())
                    font.setBold(True)
                    cell.setFont(font)

    def _oi_finished(self, results, diagnostics):
        self._oi_diagnostics = diagnostics or {}
        self.oi_meta.setText(
            f"FUTURES OI • {diagnostics.get('status') or '—'} • "
            f"{diagnostics.get('oi_available', 0)} OI • "
            f"{diagnostics.get('money_flow_hot_liquidity', 0)} HOT\n"
            f"LIQ NOW = real 5m trade flow • FLOW = 30m flow + order book • "
            f"ACTION = price + ΔOI • ZONE = flow / VWAP"
        )
        rows = []
        prepared_results = []
        for item in results or []:
            signal = self.signal_probability.futures(item)
            key = item.get("futures_ticker") or item.get("oi_root") or ""
            previous = self._oi_previous_probabilities.get(key)
            item = dict(item)
            item.update({
                "signal": signal["signal"],
                "signal_probability": signal["probability"],
                "long_probability": signal["long_probability"],
                "short_probability": signal["short_probability"],
                "signal_model": signal["signal_model"],
                "signal_probability_delta": (
                    round(signal["probability"] - previous, 1)
                    if previous is not None else None
                ),
            })
            self._oi_previous_probabilities[key] = signal["probability"]
            prepared_results.append(item)

        for index, item in enumerate(prepared_results, 1):
            oi = item.get("oi_analysis") or {}
            rows.append([
                numeric(item.get("money_flow_rank") or index),
                str(item.get("oi_root") or item.get("futures_root") or "—"),
                str(item.get("futures_ticker") or "—"),
                str(item.get("underlying_ticker") or "—"),
                numeric(self._signed(item.get("change_percent"), 2)),
                numeric(self._fmt(oi.get("oi"), 0)),
                numeric(self._signed(oi.get("oi_change_percent"), 2)),
                numeric(self._money(item.get("turnover_rub"))),
                self._liquidity_text(item),
                self._flow_text(item),
                "—",
                "—",
                "—",
                self._action_text(item),
                self._zone_text(item),
                str(item.get("signal") or "—"),
                numeric(
                    f"{self._fmt(item.get('signal_probability'), 1)}%"
                    if item.get("signal_probability") is not None else "—"
                ),
                numeric(
                    f"{self._signed(item.get('signal_probability_delta'), 1)}%"
                    if item.get("signal_probability_delta") is not None else "NEW"
                ),
            ])
        self.oi_table.set_rows(rows)
        self._highlight_money_rows(prepared_results)
        for row_index, item in enumerate(prepared_results):
            signal = str(item.get('signal') or '')
            brush = QBrush(QColor('#69e59a' if signal == 'LONG' else '#ff7d7d' if signal == 'SHORT' else '#c9d0d6'))
            signal_cell = self.oi_table.item(row_index, 15)
            if signal_cell:
                signal = str(item.get("signal") or "").upper()
                signal_cell.setText({
                    "LONG": "🟢 LONG",
                    "SHORT": "🔴 SHORT",
                    "NEUTRAL": "⚪ NEUTRAL",
                }.get(signal, "⚪ —"))
                signal_cell.setForeground(QColor("#e6e9ed"))
            for col in (16, 17):
                cell = self.oi_table.item(row_index, col)
                if cell:
                    cell.setForeground(QColor("#c9d0d6"))
        self.oi_table.setToolTip(
            "GREEN ROW — top 5 futures by real current-day monetary turnover "
            "(VALTODAY / available Price×Volume-style notional). "
            "LIQ NOW — highest real BCS trade activity over the last 5 minutes. "
            "FLOW — observed 30-minute money flow with the current order book. "
            "BOOK/TAPE/FLOW RT — live BCS WebSocket order-book and anonymized-trade pressure; these are observed-flow scores, not probabilities. "
            "ACTION — inferred position structure from price and ΔOI; no specific participant is identified. "
            "ZONE — dominant flow / VWAP range. DAY ₽ = actual VALTODAY."
        )
        self.oi_table.setVisible(bool(rows))
        if not rows:
            self.oi_meta.setText(self.oi_meta.text() + "\nNo data available.")
        self._append_oi_diagnostics()
        self._start_realtime(prepared_results)

    def _start_realtime(self, prepared_results):
        if self.realtime_thread is not None and self.realtime_thread.isRunning():
            return
        instruments = []
        seen = set()
        for item in prepared_results or []:
            ticker = str(item.get("futures_ticker") or "").upper()
            class_code = str(item.get("futures_class_code") or "SPBFUT").upper()
            if ticker and class_code and (ticker, class_code) not in seen:
                instruments.append({"ticker": ticker, "classCode": class_code})
                seen.add((ticker, class_code))
        for item in getattr(self, "_spot_results_for_realtime", [])[:10]:
            ticker = str(item.get("spot_ticker") or "").upper()
            class_code = str(item.get("spot_class_code") or item.get("class_code") or "TQBR").upper()
            if ticker and class_code and (ticker, class_code) not in seen:
                instruments.append({"ticker": ticker, "classCode": class_code})
                seen.add((ticker, class_code))
        if not instruments:
            return
        self._oi_diagnostics.update({
            "realtime_source": "BCS_WEBSOCKET_MARKET_DATA",
            "realtime_policy": "READ_ONLY_REALTIME_BOOK_TAPE; TOP_SPOT_10_PLUS_ACTIVE_FUTURES",
            "realtime_subscriptions": len(instruments),
        })
        self._append_oi_diagnostics()
        api = getattr(self.oi_worker.service, "api", None) if self.oi_worker is not None else None
        if api is None:
            api = FuturesOIMarketDataScannerService().api
        self.realtime_thread = QThread(self)
        self.realtime_worker = RealtimeMicrostructureWorker(api, instruments)
        self.realtime_worker.moveToThread(self.realtime_thread)
        self.realtime_thread.started.connect(self.realtime_worker.run)
        self.realtime_worker.snapshot.connect(self._realtime_snapshot)
        self.realtime_worker.status.connect(self._realtime_status)
        self.realtime_worker.failed.connect(self._realtime_failed)
        self.realtime_worker.finished.connect(self.realtime_thread.quit)
        self.realtime_thread.finished.connect(self._realtime_thread_finished)
        self.realtime_thread.start()

    def _realtime_snapshot(self, item):
        self._realtime_by_ticker[item.get("ticker")] = item
        ticker = str(item.get("ticker") or "").upper()
        book = item.get("book_score")
        tape = item.get("tape_score")
        flow = item.get("flow_score")
        book_text = f"{book:.0f}" if book is not None else "—"
        tape_text = f"{tape:.0f}" if tape is not None else "—"
        flow_text = f"{flow:.0f}" if flow is not None else "—"
        for row in range(self.oi_table.rowCount()):
            contract = self.oi_table.item(row, 2)
            if contract and contract.text().strip().upper() == ticker:
                self.oi_table.item(row, 10).setText(book_text)
                self.oi_table.item(row, 11).setText(tape_text)
                self.oi_table.item(row, 12).setText(flow_text)
        for table in (getattr(self, "result_table", None), getattr(self, "weak_result_table", None)):
            if table is None:
                continue
            for row in range(table.rowCount()):
                cell = table.item(row, 1)
                if cell and cell.text().strip().upper() == ticker:
                    table.item(row, 16).setText(book_text)
                    table.item(row, 17).setText(tape_text)
                    table.item(row, 18).setText(flow_text)

    def _realtime_status(self, status):
        state = str(status.get("state") or "—")
        if state == "LIVE":
            self.oi_meta.setText(self.oi_meta.text().split("\n")[0] + " • REALTIME BOOK/TAPE: LIVE")
        elif state == "RECONNECTING":
            self.oi_meta.setText(self.oi_meta.text().split("\n")[0] + " • REALTIME: RECONNECTING")

    def _realtime_failed(self, error):
        self._oi_diagnostics["realtime_error"] = error
        self._append_oi_diagnostics()

    def _stop_realtime(self):
        if self.realtime_worker is not None:
            self.realtime_worker.stop()
        if self.realtime_thread is not None and self.realtime_thread.isRunning():
            self.realtime_thread.quit()

    def _realtime_thread_finished(self):
        if self.realtime_thread is not None:
            self.realtime_thread.deleteLater()
        self.realtime_thread = None
        self.realtime_worker = None

    def closeEvent(self, event):
        # Stop worker threads before Qt destroys their QThread owners.
        self._stop_realtime()

        if self.realtime_thread is not None and self.realtime_thread.isRunning():
            self.realtime_thread.quit()
            self.realtime_thread.wait(4000)

        if self.oi_thread is not None and self.oi_thread.isRunning():
            self.oi_thread.quit()
            self.oi_thread.wait(4000)

        if self.scan_thread is not None and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait(4000)

        super().closeEvent(event)

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
        self.oi_meta.setText(f"FUTURES OI\n\nFutures OI analysis error: {error}")
        self._append_oi_diagnostics()

    def _oi_thread_finished(self):
        if self.oi_thread is not None:
            self.oi_thread.deleteLater()
        self.oi_thread = None
        self.oi_worker = None
