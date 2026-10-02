"""FINAL RADAR — the small final shortlist after repeated confirmation."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui_table import CopyableTableWidget, RADAR_BUTTON_STYLE

from services.final_radar_service import FinalRadarService


class FinalRadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = FinalRadarService()
        self._rows = []
        self._realtime_render_timer = QTimer(self)
        self._realtime_render_timer.setSingleShot(True)
        self._realtime_render_timer.timeout.connect(self._render)
        self._build()

    def _build(self):
        self.setStyleSheet("""
            QLabel#frTitle { font-size:17px; font-weight:800; color:#e8ecef; }
            QLabel#frMeta { font-size:11px; color:#8d98a2; }
            QPushButton { background:#30383f; color:#f0f2f4; border:1px solid #4a555f;
                          border-radius:7px; padding:8px 13px; font-weight:700; }
            QTableWidget { background:#171b20; color:#dfe3e7; border:1px solid #394149;
                           gridline-color:#2d343b; font-size:11px; }
            QHeaderView::section { background:#252c33; color:#b9c2ca; padding:7px;
                                   border:0; border-bottom:1px solid #414a52; font-weight:700; }
        """)
        self.setStyleSheet(self.styleSheet() + RADAR_BUTTON_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("FINAL RADAR")
        title.setObjectName("frTitle")
        head.addWidget(title)
        self.state = QLabel("WAITING")
        self.state.setStyleSheet("font-size:12px;font-weight:800;color:#d4af55;")
        head.addWidget(self.state)
        head.addStretch(1)
        self.copy_button = QPushButton("COPY")
        self.copy_button.setToolTip("Copy FINAL RADAR status and all rows to the clipboard")
        self.copy_button.clicked.connect(self.copy_table)
        head.addWidget(self.copy_button)
        root.addLayout(head)

        self.meta = QLabel(
            "FINAL • SPOT + FUTURES • REALTIME • "
            "3 consecutive confirmations • liquid instruments only • read-only"
        )
        self.meta.setObjectName("frMeta")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.table = CopyableTableWidget(0, 12)
        self.table.setHorizontalHeaderLabels([
            "#", "Type", "Instrument", "Direction", "Phase", "Δ%", "TODAY ₽×V", "ATR / USED",
            "PROB", "Scans", "RT", "FUTURES",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setShowGrid(False)
        self.table.setToolTip(
            "TODAY ₽×V = accumulated real turnover from the trading-day open: SPOT session money, FUTURES MOEX VALTODAY. FINAL RADAR promotes only liquid candidates that survive three consecutive "
            "strict scans and have real-time confirmation from at least two live "
            "BOOK/TAPE/FLOW components. SPOT uses the established SPOT liquidity gate; "
            "futures use existing OI/Money Flow liquidity data. Matching futures are "
            "context for SPOT and do not suppress an otherwise valid SPOT candidate. "
            "This is a read-only confirmation list, not an order signal."
        )
        root.addWidget(self.table, 1)

        self.note = QLabel(
            "FINAL means data chain confirmed, not guaranteed profit. "
            "If confirmation breaks, the instrument leaves FINAL automatically."
        )
        self.note.setWordWrap(True)
        self.note.setStyleSheet("font-size:10px;color:#7f8a94;padding:4px;")
        root.addWidget(self.note)

    @staticmethod
    def _fmt(value, digits=1, signed=False):
        try:
            number = float(value)
            return (
                f"{number:+,.{digits}f}".replace(",", " ")
                if signed
                else f"{number:,.{digits}f}".replace(",", " ")
            )
        except (TypeError, ValueError):
            return "—"

    @staticmethod
    def _money(value):
        try:
            value = float(value)
            if value >= 1_000_000_000:
                return f"{value / 1_000_000_000:.2f}B"
            if value >= 1_000_000:
                return f"{value / 1_000_000:.2f}M"
            if value >= 1_000:
                return f"{value / 1_000:.1f}K"
            return f"{value:.0f}"
        except (TypeError, ValueError):
            return "—"

    def _render(self, resize_columns=True):
        self._rows = self.service.final_candidates()
        status = self.service.status()
        self.table.setRowCount(len(self._rows))

        if not self._rows:
            if status["scan_no"] == 0:
                self.state.setText("WAITING FOR SCAN")
            elif status["max_confirmations"] < status["required_confirmations"]:
                left = status["required_confirmations"] - status["max_confirmations"]
                self.state.setText(
                    f"NEED {left} MORE SCAN" if left == 1 else f"NEED {left} MORE SCANS"
                )
            elif status.get("rt_ready", 0) == 0 and status.get("strict_candidates", 0):
                self.state.setText(f"BLOCKED • RT < {self.service.MIN_RT_SCORE:.0f}")
            else:
                self.state.setText("NO FINAL CANDIDATE")
        else:
            self.state.setText(
                f"{len(self._rows)} FINAL • "
                f"SPOT {status.get('final_spot_count', 0)} • "
                f"FUTURES {status.get('final_futures_count', 0)}"
            )

        self.meta.setText(
            f"SCAN {status['scan_no']} • STRICT {status['strict_candidates']} • "
            f"FINAL SPOT {status.get('final_spot_count', 0)} • "
            f"FINAL FUTURES {status.get('final_futures_count', 0)} • "
            f"RT READY {status.get('rt_ready', 0)} • "
            f"RT BLOCKED {status.get('rt_blocked', 0)}"
        )

        for row, item in enumerate(self._rows, 1):
            rt = item["final_realtime"]
            futures = item["final_futures"]
            rt_text = f"{rt['average']:.0f} • {rt['count']}/3"
            instrument_type = str(item.get("final_instrument_type") or "—")
            fut_text = "—"
            if instrument_type == "FUTURES":
                fut_text = f"✓ OI/FLOW • {futures['probability']:.0f}%"
            elif futures["state"] == "CONFIRMED":
                fut_text = f"✓ {futures['contract']} • {futures['probability']:.0f}%"
            elif futures["state"] == "CONFLICT":
                fut_text = "CONFLICT"
            elif futures["state"] == "NO_MATCH":
                fut_text = "NO MATCH"

            is_futures = instrument_type == "FUTURES"
            values = [
                str(row),
                instrument_type,
                str(item.get("futures_ticker") if is_futures else item.get("spot_ticker") or "—"),
                "🟢 LONG" if item.get("signal") == "LONG" else "🔴 SHORT",
                "OI/FLOW" if is_futures else str(item.get("move_phase") or "—"),
                self._fmt(item.get("change_percent"), 2, True),
                self._money(item.get("turnover_rub") if is_futures else item.get("session_money")),
                "—" if is_futures else f"{self._fmt(item.get('atr_percent'), 1)}% • {self._fmt(item.get('atr_used_percent'), 0)}%",
                f"{self._fmt(item.get('signal_probability'), 1)}%",
                f"{item.get('final_confirmations', 0)}/3",
                rt_text,
                fut_text,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row - 1, col, cell)
                cell.setBackground(QBrush(QColor("#123f2a")))
                if col == 2:
                    cell.setForeground(QColor("#69e59a" if item.get("signal") == "LONG" else "#ff7d7d"))
        if resize_columns:
            self.table.resizeColumnsToContents()

    def copy_table(self):
        lines = [
            "=== FINAL RADAR ===",
            f"STATE: {self.state.text()}",
            self.meta.text(),
            "",
            "\t".join([
                "#", "Type", "Instrument", "Direction", "Phase", "Δ%", "TODAY ₽×V", "ATR / USED",
                "PROB", "Scans", "RT", "FUTURES"
            ]),
        ]
        for row in range(self.table.rowCount()):
            values = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                values.append(item.text() if item is not None else "")
            lines.append("\t".join(values))
        lines.extend(["", self.note.text()])
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_button.setText("COPIED ✓")
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

    def record_spot_scan(self, market_map, day_key=None):
        self.service.record_spot_scan(market_map, day_key=day_key)
        self._render(resize_columns=True)

    def record_futures_scan(self, results, day_key=None):
        self.service.record_futures_scan(results, day_key=day_key)
        self._render(resize_columns=True)

    def update_realtime(self, snapshot, render=True):
        self.service.update_realtime(snapshot)
        # The parent window batches websocket updates. Suppress this local
        # timer when called from that batch and repaint once after the batch.
        if render and not self._realtime_render_timer.isActive():
            self._realtime_render_timer.start(250)

    def update_futures(self, results):
        self.service.update_futures(results)
        self._render()
