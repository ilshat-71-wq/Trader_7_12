"""Compact Entry Radar presentation.

Read-only presentation layer over the existing Futures OI model. It does not
create orders and does not recalculate the underlying signal model.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from services.entry_radar_service import EntryRadarService


class EntryRadarWidget(QWidget):
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
            QTableWidget::item:selected { background:#33424a; color:#f2f4f5; }
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
        self.copy_button = QPushButton("COPY")
        self.copy_button.setToolTip("Copy the visible Entry Radar table")
        self.copy_button.clicked.connect(self.copy_view)
        head.addWidget(self.copy_button)
        root.addLayout(head)

        self.meta = QLabel(
            "WHEN / WHERE • 09:00 handoff • existing Futures OI model • read-only decision support"
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
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.setShowGrid(False)
        self.table.setToolTip(
            "Instrument = futures contract • Direction = model direction • Confidence = model confidence + change • "
            "Entry = current entry state • Entry Zone = dominant flow/VWAP working range. "
            "Realtime BOOK/TAPE/FLOW RT does not overwrite model confidence."
        )
        root.addWidget(self.table, 1)

        self.note = QLabel(
            "ENTER = ≥80% + valid zone • WAIT = 65–79% + zone • "
            "WATCH = incomplete / lower confidence • AVOID = current structure does not confirm a new entry. "
            "PROB is model confidence, not profit probability. Full detail → FUTURES OI."
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

    def copy_view(self):
        headers = [
            self.table.horizontalHeaderItem(i).text()
            for i in range(self.table.columnCount())
        ]
        lines = ["ENTRY RADAR", "\t".join(headers)]
        for row in range(self.table.rowCount()):
            lines.append(
                "\t".join(
                    self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                )
            )
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_button.setText("COPIED ✓")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

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
            is_hero = row == 0 and state == "ENTER"
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
                cell = self.table.item(row, col)
                cell.setBackground(QBrush(QColor(colors[state])))
                if is_hero:
                    cell.setFont(cell.font())
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)
            self.table.item(row, 3).setForeground(QColor(foregrounds[state]))
            if is_hero:
                self.table.item(row, 0).setForeground(QColor("#e8ecef"))
                self.table.item(row, 2).setForeground(QColor("#e8ecef"))
                self.table.item(row, 4).setForeground(QColor("#d9e4dc"))
            self.table.item(row, 3).setText(f"🟢 ENTER" if state == "ENTER" else
                                            f"🟡 WAIT" if state == "WAIT" else
                                            f"⚪ WATCH" if state == "WATCH" else
                                            f"🔴 AVOID")
