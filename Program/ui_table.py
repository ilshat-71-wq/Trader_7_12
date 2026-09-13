"""Reusable professional Qt tables for Trader_7_12 Pro."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
)


TABLE_STYLE = """
QTableWidget {
    background: #171b20;
    color: #dfe3e7;
    border: 1px solid #394149;
    border-radius: 8px;
    gridline-color: #2d343b;
    selection-background-color: #33424a;
    selection-color: #ffffff;
    alternate-background-color: #1b2025;
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 12px;
}
QTableWidget::item {
    padding: 5px 8px;
}
QHeaderView::section {
    background: #252c33;
    color: #b9c2ca;
    border: 0;
    border-bottom: 1px solid #414a52;
    padding: 8px 7px;
    font-weight: 700;
    font-size: 11px;
}
QHeaderView::section:hover {
    background: #2d353d;
    color: #e8ecef;
}
QTableCornerButton::section {
    background: #252c33;
    border: 0;
}
QScrollBar:vertical {
    background: #171b20;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #46515a;
    min-height: 28px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


class _SortableItem(QTableWidgetItem):
    def __lt__(self, other):
        left = self.data(Qt.ItemDataRole.UserRole)
        right = other.data(Qt.ItemDataRole.UserRole)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left < right
        return super().__lt__(other)


class MarketTableWidget(QTableWidget):
    """Professional read-only table with sorting and copy-friendly TSV export."""

    def __init__(self, columns, widths=None, parent=None):
        super().__init__(0, len(columns), parent)
        self.setHorizontalHeaderLabels(columns)
        self.setStyleSheet(TABLE_STYLE)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(30)

        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setHighlightSections(False)
        for index in range(len(columns)):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)

        if widths:
            for index, width in enumerate(widths):
                self.setColumnWidth(index, width)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def set_rows(self, rows):
        self.setSortingEnabled(False)
        self.setUpdatesEnabled(False)
        self.clearContents()
        self.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                text = "—" if value is None or value == "" else str(value)
                item = _SortableItem(text)

                if isinstance(value, _NumericCell):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                    )
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        _numeric_sort_value(text),
                    )
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                    )

                self.setItem(row_index, column_index, item)

        self.setUpdatesEnabled(True)
        self.setSortingEnabled(True)

    def _selected_rows(self):
        return sorted({index.row() for index in self.selectedIndexes()})

    def copy_selection(self, include_headers=True):
        """Copy selected rows as TSV for Numbers, Excel, Telegram and plain text."""
        rows = self._selected_rows()
        if not rows:
            rows = list(range(self.rowCount()))
        if not rows:
            return False

        lines = []
        if include_headers:
            lines.append(
                "\t".join(
                    self.horizontalHeaderItem(i).text()
                    for i in range(self.columnCount())
                )
            )

        for row in rows:
            lines.append(
                "\t".join(
                    self.item(row, column).text() if self.item(row, column) else ""
                    for column in range(self.columnCount())
                )
            )

        QApplication.clipboard().setText("\n".join(lines))
        return True

    def copy_all(self):
        return self.copy_selection(include_headers=True)

    def copy_without_headers(self):
        return self.copy_selection(include_headers=False)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
            event.accept()
            return
        super().keyPressEvent(event)

    def _show_context_menu(self, position):
        menu = QMenu(self)
        copy_action = menu.addAction("Копировать выбранные строки")
        copy_action.triggered.connect(self.copy_selection)
        copy_all_action = menu.addAction("Копировать всю таблицу")
        copy_all_action.triggered.connect(self.copy_all)
        copy_plain_action = menu.addAction("Копировать без заголовков")
        copy_plain_action.triggered.connect(self.copy_without_headers)
        menu.addSeparator()
        select_all_action = menu.addAction("Выделить всё")
        select_all_action.triggered.connect(self.selectAll)
        menu.exec(self.viewport().mapToGlobal(position))


class _NumericCell(str):
    """Marker used by table builders for right-aligned/sortable numeric cells."""


def _numeric_sort_value(text):
    if text in {"—", "-", ""}:
        return float("-inf")

    raw = text.replace("\u00a0", " ").replace("₽", "").strip()
    multiplier = 1.0

    for suffix, factor in (
        ("млрд", 1_000_000_000.0),
        ("млн", 1_000_000.0),
        ("тыс", 1_000.0),
    ):
        if raw.endswith(suffix):
            raw = raw[: -len(suffix)].strip()
            multiplier = factor
            break

    raw = raw.replace(" ", "").replace("%", "").replace("+", "")
    try:
        return float(raw) * multiplier
    except ValueError:
        return float("-inf")


def numeric(value):
    return _NumericCell(str(value))
