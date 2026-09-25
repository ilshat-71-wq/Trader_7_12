"""MOVE RADAR presentation over the existing SPOT market map."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.move_radar_service import MoveRadarService


class MoveRadarWidget(QWidget):
    """Compact phase radar. It never scans data itself."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._build()

    def _build(self):
        self.setStyleSheet("""
            QLabel#mvTitle { font-size:17px; font-weight:800; color:#e8ecef; }
            QLabel#mvMeta { font-size:11px; color:#8d98a2; }
            QPushButton { background:#30383f; color:#f0f2f4; border:1px solid #4a555f;
                          border-radius:7px; padding:8px 13px; font-weight:700; }
            QPushButton:hover { background:#39434c; }
            QTableWidget { background:#171b20; color:#dfe3e7; border:1px solid #394149;
                           gridline-color:#2d343b; font-size:11px; }
            QTableWidget::item:selected { background:#33424a; color:#f2f4f5; }
            QHeaderView::section { background:#252c33; color:#b9c2ca; padding:7px;
                                   border:0; border-bottom:1px solid #414a52; font-weight:700; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("MOVE RADAR")
        title.setObjectName("mvTitle")
        head.addWidget(title)
        self.state = QLabel("NO DATA")
        self.state.setStyleSheet("font-size:12px;font-weight:800;color:#d4af55;")
        head.addWidget(self.state)
        head.addStretch(1)
        self.copy_button = QPushButton("COPY")
        self.copy_button.clicked.connect(self.copy_view)
        head.addWidget(self.copy_button)
        root.addLayout(head)

        self.meta = QLabel(
            "WHERE IS THE MOVE • existing SPOT market map • phase only • no new scan • read-only"
        )
        self.meta.setObjectName("mvMeta")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels([
            "Ticker", "Phase", "Direction", "Price Δ%", "ATR / USED",
            "RS", "₽/min", "15m", "Accel", "PROB", "RT",
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setShowGrid(False)
        self.table.setToolTip(
            "START = large aligned move, low ATR usage and rising directional acceleration. "
            "DEVELOPING = move is underway. LATE = much of the normal daily range is used. "
            "EXHAUSTION = >100% ATR or high ATR usage with weakening directional acceleration. "
            "RT = live BOOK/TAPE/FLOW RT when available. This is a phase filter, not an order signal."
        )
        root.addWidget(self.table, 1)

        self.note = QLabel(
            "START is deliberately strict: |Price Δ| ≥ 1%, PROB ≥ 80%, ATR USED ≤ 40%, "
            "and directional Accel ≥ +20%. Conflicting price/signal direction is excluded. "
            "PROB is model confidence, not profit probability."
        )
        self.note.setWordWrap(True)
        self.note.setStyleSheet("font-size:10px;color:#7f8a94;padding:4px;")
        root.addWidget(self.note)

    @staticmethod
    def _fmt(value, digits=1, signed=False):
        try:
            number = float(value)
            if signed:
                return f"{number:+,.{digits}f}".replace(",", " ")
            return f"{number:,.{digits}f}".replace(",", " ")
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

    @staticmethod
    def _rt_text(item):
        rt = item.get("_realtime") or {}
        parts = []
        for key in ("book_score", "tape_score", "flow_score"):
            value = rt.get(key)
            parts.append(f"{float(value):.0f}" if value is not None else "—")
        return "/".join(parts)

    def set_results(self, market_map):
        self._rows = [dict(x) for x in MoveRadarService.candidates(market_map)]
        self._render()

    def update_realtime(self, snapshot):
        ticker = str((snapshot or {}).get("ticker") or "").upper()
        if not ticker:
            return
        for item in self._rows:
            if str(item.get("spot_ticker") or "").upper() == ticker:
                item["_realtime"] = dict(snapshot)
        self._render()

    def copy_view(self):
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        lines = ["MOVE RADAR", "\t".join(headers)]
        for row in range(self.table.rowCount()):
            lines.append("\t".join(
                self.table.item(row, col).text() if self.table.item(row, col) else ""
                for col in range(self.table.columnCount())
            ))
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_button.setText("COPIED ✓")
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

    def _render(self):
        rows = list(self._rows)
        phase_colors = {
            "START": "#123f2a",
            "DEVELOPING": "#263326",
            "LATE": "#3a3520",
            "EXHAUSTION": "#3a272b",
        }
        phase_labels = {
            "START": "🟢 START",
            "DEVELOPING": "🟢 DEVELOPING",
            "LATE": "🟡 LATE",
            "EXHAUSTION": "🔴 EXHAUSTION",
        }
        self.table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            signal = str(item.get("signal") or "").upper()
            values = [
                str(item.get("spot_ticker") or "—"),
                phase_labels.get(item.get("move_phase"), "—"),
                "🟢 LONG" if signal == "LONG" else "🔴 SHORT",
                self._fmt(item.get("change_percent"), 2, signed=True),
                (
                    f"{self._fmt(item.get('atr_percent'))}% • "
                    f"{self._fmt(item.get('atr_used_percent'), 0)}%"
                ),
                self._fmt(item.get("relative_strength"), 2, signed=True),
                self._money(item.get("money_per_minute")),
                self._money(item.get("recent_money")),
                self._fmt(item.get("money_acceleration"), 1, signed=True),
                self._fmt(item.get("signal_probability"), 1) + "%",
                self._rt_text(item),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter if col in (1, 2, 3, 4, 5, 7, 8, 9, 10)
                    else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, col, cell)
                cell.setBackground(QBrush(QColor(phase_colors[item["move_phase"]])))
            self.table.item(row, 1).setForeground(QColor(
                "#69e59a" if item["move_phase"] == "START"
                else "#d4af55" if item["move_phase"] == "LATE"
                else "#ff7d7d" if item["move_phase"] == "EXHAUSTION"
                else "#b9e0c2"
            ))
        self.state.setText(f"{len(rows)} CANDIDATES")
