"""Compact Entry Radar presentation.

Read-only presentation layer over the existing Futures OI model. It does not
create orders and does not recalculate the underlying signal model.
"""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from services.entry_radar_service import EntryRadarService


class EntryRadarWidget(QWidget):
    entry_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._build()

    def _build(self):
        self.setStyleSheet("""
            QLabel#erTitle { font-size:17px; font-weight:800; color:#e8ecef; }
            QLabel#erMeta { font-size:11px; color:#8d98a2; }
            QPushButton { background:#30383f; color:#f0f2f4; border:1px solid #4a555f;
                          border-radius:7px; padding:8px 13px; font-weight:700; }
            QPushButton:hover { background:#39434c; }
            QTableWidget { background:#171b20; color:#dfe3e7; border:1px solid #394149;
                           gridline-color:#2d343b; font-size:12px; }
            QHeaderView::section { background:#252c33; color:#b9c2ca; padding:8px;
                                   border:0; border-bottom:1px solid #414a52; font-weight:700; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("ENTRY RADAR")
        title.setObjectName("erTitle")
        head.addWidget(title)
        head.addStretch(1)
        self.refresh_button = QPushButton("REFRESH FROM OI")
        self.refresh_button.clicked.connect(self.refresh_from_source)
        head.addWidget(self.refresh_button)
        self.start_button = QPushButton("START ENTRY SESSION")
        self.start_button.clicked.connect(self.entry_requested.emit)
        head.addWidget(self.start_button)
        root.addLayout(head)

        self.meta = QLabel(
            "WHEN / WHERE • 10:00 MSK main session • compact view of the existing "
            "Futures OI model • ENTER/WAIT/WATCH/AVOID are model states, not order commands"
        )
        self.meta.setObjectName("erMeta")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Инструмент", "Направление", "Confidence", "Entry", "Entry Zone"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.note = QLabel(
            "ENTRY = confidence ≥ 80% + valid zone; WAIT = 65–79%; "
            "WATCH = 55–64% or incomplete setup; AVOID = confidence < 55% "
            "or a liquidation conflict. The full professional table remains in FUTURES OI."
        )
        self.note.setWordWrap(True)
        self.note.setStyleSheet("font-size:10px;color:#7f8a94;padding:4px;")
        root.addWidget(self.note)

    def set_results(self, results):
        self._rows = [dict(item) for item in (results or [])]
        self._render()

    def refresh_from_source(self):
        if self._rows:
            self._render()

    def update_realtime(self, snapshot):
        ticker = str((snapshot or {}).get("ticker") or "").upper()
        if not ticker:
            return
        for item in self._rows:
            if str(item.get("futures_ticker") or "").upper() == ticker:
                item["_realtime"] = dict(snapshot)
        # Realtime is intentionally informational here; it does not overwrite
        # the D1/OI signal or confidence.
        self._render()

    def _render(self):
        rows = sorted(
            self._rows,
            key=lambda x: (
                {"ENTER": 0, "WAIT": 1, "WATCH": 2, "AVOID": 3}.get(EntryRadarService.state(x), 4),
                -(float(x.get("signal_probability") or 0)),
            ),
        )
        self.table.setRowCount(len(rows))
        colors = {
            "ENTER": "#123f2a",
            "WAIT": "#3a3520",
            "WATCH": "#252b31",
            "AVOID": "#3a272b",
        }
        foregrounds = {
            "ENTER": "#69e59a",
            "WAIT": "#d4af55",
            "WATCH": "#b9c1c8",
            "AVOID": "#ff7d7d",
        }
        for row, item in enumerate(rows):
            state = EntryRadarService.state(item)
            values = [
                str(item.get("futures_ticker") or item.get("futures_root") or "—"),
                EntryRadarService.direction_label(item),
                EntryRadarService.confidence_text(item),
                state,
                EntryRadarService.zone_text(item),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col in (1, 2, 3) else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, col, cell)
            for col in range(self.table.columnCount()):
                self.table.item(row, col).setBackground(QBrush(QColor(colors[state])))
            self.table.item(row, 3).setForeground(QColor(foregrounds[state]))
            self.table.item(row, 3).setText(f"🟢 ENTER" if state == "ENTER" else
                                            f"🟡 WAIT" if state == "WAIT" else
                                            f"⚪ WATCH" if state == "WATCH" else
                                            f"🔴 AVOID")
