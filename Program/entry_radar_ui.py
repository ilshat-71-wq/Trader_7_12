"""Compact Entry Radar presentation for SPOT and Futures.

Read-only presentation layer over the existing market models. It does not
create orders and does not recalculate the underlying signal model.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
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
from services.entry_radar_service import EntryRadarService


class EntryRadarWidget(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._realtime_render_timer = QTimer(self)
        self._realtime_render_timer.setSingleShot(True)
        self._realtime_render_timer.timeout.connect(self._render)
        self._build()

    def _build(self):
        self.setStyleSheet(
            """
            QLabel#erTitle { font-size:17px; font-weight:800; color:#e8ecef; }
            QLabel#erMeta { font-size:11px; color:#8d98a2; }
            QTableWidget { background:#171b20; color:#dfe3e7; border:1px solid #394149;
                           gridline-color:#2d343b; font-size:12px; }
            QTableWidget::item:selected { background:#33424a; color:#f2f4f5; }
            QHeaderView::section { background:#252c33; color:#b9c2ca; padding:8px;
                                   border:0; border-bottom:1px solid #414a52; font-weight:700; }
            """
            + RADAR_BUTTON_STYLE
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("ENTRY RADAR")
        title.setObjectName("erTitle")
        head.addWidget(title)
        self.state = QLabel("NO DATA")
        self.state.setStyleSheet("font-size:12px;font-weight:800;color:#d4af55;")
        head.addWidget(self.state)
        head.addStretch(1)

        self.refresh_button = QPushButton("REFRESH")
        self.refresh_button.setToolTip("Refresh Morning Radar + Futures OI inputs")
        self.refresh_button.clicked.connect(self.refresh_from_source)
        head.addWidget(self.refresh_button)

        self.copy_button = QPushButton("COPY")
        self.copy_button.setToolTip("Copy the visible Entry Radar table")
        self.copy_button.clicked.connect(self.copy_view)
        head.addWidget(self.copy_button)
        root.addLayout(head)

        self.meta = QLabel(
            "SPOT + FUTURES • morning handoff + current OI • read-only decision support"
        )
        self.meta.setObjectName("erMeta")
        self.meta.setWordWrap(True)
        root.addWidget(self.meta)

        self.table = CopyableTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Type", "Инструмент", "Направление", "Confidence", "Entry", "Entry Zone"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setShowGrid(False)
        self.table.setToolTip(
            "Type = SPOT or FUTURES. Instrument is the real market ticker/contract. "
            "Confidence = existing model confidence + change. Entry = existing read-only entry-state logic. "
            "Entry Zone is shown only when the source provides a real working zone. "
            "Missing zone remains WATCH; no synthetic level is created."
        )
        root.addWidget(self.table, 1)

        self.note = QLabel(
            "ENTER = ≥80% + valid real zone • WAIT = 65–79% + valid real zone • "
            "WATCH = incomplete / lower confidence / missing zone • AVOID = current structure does not confirm a new entry. "
            "SPOT rows remain eligible for the common radar but are not assigned a synthetic entry zone."
        )
        self.note.setWordWrap(True)
        self.note.setStyleSheet("font-size:10px;color:#7f8a94;padding:4px;")
        root.addWidget(self.note)

    @staticmethod
    def _instrument_type(item):
        value = str(
            item.get("instrument_type")
            or item.get("final_instrument_type")
            or ""
        ).upper()
        if value in {"SPOT", "FUTURES"}:
            return value
        return "FUTURES" if item.get("futures_ticker") or item.get("futures_root") else "SPOT"

    @classmethod
    def _instrument(cls, item):
        if cls._instrument_type(item) == "FUTURES":
            return str(item.get("futures_ticker") or item.get("futures_root") or "—")
        return str(item.get("spot_ticker") or item.get("ticker") or "—")

    def set_results(self, results):
        self._rows = [dict(item) for item in (results or [])]
        self._render()

    def refresh_from_source(self):
        self.refresh_requested.emit()

    def copy_view(self):
        headers = [
            self.table.horizontalHeaderItem(i).text()
            for i in range(self.table.columnCount())
        ]
        lines = ["ENTRY RADAR", "	".join(headers)]
        for row in range(self.table.rowCount()):
            lines.append(
                "	".join(
                    self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                )
            )
        QApplication.clipboard().setText("
".join(lines))
        self.copy_button.setText("COPIED ✓")
        QTimer.singleShot(1400, lambda: self.copy_button.setText("COPY"))

    def update_realtime(self, snapshot, render=True):
        ticker = str((snapshot or {}).get("ticker") or "").upper()
        if not ticker:
            return
        for item in self._rows:
            if self._instrument(item).upper() == ticker:
                item["_realtime"] = dict(snapshot)
        if render and not self._realtime_render_timer.isActive():
            self._realtime_render_timer.start(250)

    def _render(self):
        rows = sorted(
            self._rows,
            key=lambda x: (
                {"ENTER": 0, "WAIT": 1, "WATCH": 2, "AVOID": 3}.get(
                    EntryRadarService.state(x), 4
                ),
                -(float(x.get("signal_probability") or 0)),
            ),
        )
        self.table.setRowCount(len(rows))

        for row, item in enumerate(rows):
            state = EntryRadarService.state(item)
            signal = str(item.get("signal") or "").upper()
            direction = EntryRadarService.direction_label(item)
            probability_text = EntryRadarService.confidence_text(item)
            instrument_type = self._instrument_type(item)
            instrument = self._instrument(item)

            values = [
                instrument_type,
                instrument,
                direction,
                probability_text,
                state,
                EntryRadarService.zone_text(item),
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                    if col in (0, 2, 3, 4)
                    else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row, col, cell)

            bg = {
                "ENTER": "#123f2a",
                "WAIT": "#3a3520",
                "WATCH": "#252b31",
                "AVOID": "#3a272b",
            }.get(state, "#252b31")
            fg = {
                "ENTER": "#69e59a",
                "WAIT": "#d4af55",
                "WATCH": "#b9c1c8",
                "AVOID": "#ff7d7d",
            }.get(state, "#b9c1c8")
            for col in range(self.table.columnCount()):
                self.table.item(row, col).setBackground(QBrush(QColor(bg)))
            self.table.item(row, 1).setForeground(
                QColor("#69e59a" if signal == "LONG" else "#ff7d7d" if signal == "SHORT" else "#e6e9ed")
            )
            self.table.item(row, 4).setForeground(QColor(fg))

        self.state.setText(f"{len(rows)} ROWS" if rows else "NO DATA")
