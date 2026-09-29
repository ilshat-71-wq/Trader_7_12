from PySide6.QtWidgets import QTableWidgetItem

from ui_table import CopyableTableWidget


def test_copyable_table_numeric_sort_key():
    low = CopyableTableWidget._sort_key(QTableWidgetItem("91.0% ↑"))
    high = CopyableTableWidget._sort_key(QTableWidgetItem("93.0% ↑"))
    assert low < high


def test_copyable_table_ticker_sort_key_is_textual():
    siz6 = CopyableTableWidget._sort_key(QTableWidgetItem("SIZ6"))
    siz5 = CopyableTableWidget._sort_key(QTableWidgetItem("SIZ5"))
    assert siz5 < siz6
