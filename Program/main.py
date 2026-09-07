"""Trader_7_12 Pro — main launcher.

Read-only market-information scanner with futures/OI context. No order execution.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from oi_watchlist_ui import OIWatchlistTraderWindow


def main():
    print("🚀 Запуск Trader_7_12 Pro — Market Information Radar")

    app = QApplication(sys.argv)
    app.setApplicationName("Trader_7_12 Pro")
    app.setQuitOnLastWindowClosed(True)

    window = OIWatchlistTraderWindow(scanner_enabled=True)
    window.show()
    window.raise_()
    window.activateWindow()

    print(f"🖥️ GUI window visible: {window.isVisible()}")
    print(f"🖥️ GUI platform: {app.platformName()}")

    QTimer.singleShot(0, window._update_session_header)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
