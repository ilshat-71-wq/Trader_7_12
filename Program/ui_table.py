"""Reusable professional Qt tables for Trader_7_12 Pro."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem


TABLE_STYLE = """
QTableWidget {
    background: #171b20;
    color: #dfe3e7;
    border: 1px solid #394149;
    border-radius: 8px;
    gridline-color: #2d343b;
    selection-background-color: #303a43;
    selection-color: #f3f5f6;
    alternate-background-color: #1b2025;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
}
QTableWidget::item { padding: 4px 6px; }
QHeaderView::section {
    background: #252c33;
    color: #aeb7bf;
    border: 0;
    border-bottom: 1px solid #414a52;
    padding: 7px 6px;
    font-weight: 700;
    font-size: 11px;
}
QTableCornerButton::section { background: #252c33; border: 0; }
"""


class MarketTableWidget(QTableWidget):
    """Compact, non-wrapping table with stable numeric alignment."""

    def __init__(self, columns, widths=None, parent=None):
        super().__init__(0, len(columns), parent)
        self.setHorizontalHeaderLabels(columns)
        self.setStyleSheet(TABLE_STYLE)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSortingEnabled(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(30)
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(True)
        for index in range(len(columns)):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
        if widths:
            for index, width in enumerate(widths):
                self.setColumnWidth(index, width)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def set_rows(self, rows):
        self.setUpdatesEnabled(False)
        self.clearContents()
        self.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem("—" if value is None or value == "" else str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (
                    Qt.AlignmentFlag.AlignRight if isinstance(value, _NumericCell) else Qt.AlignmentFlag.AlignLeft
                ))
                self.setItem(row_index, column_index, item)
        self.setUpdatesEnabled(True)
        self.resizeRowsToContents()


class _NumericCell(str):
    """Marker used by table builders for right-aligned numeric cells."""


def numeric(value):
    return _NumericCell(str(value))
