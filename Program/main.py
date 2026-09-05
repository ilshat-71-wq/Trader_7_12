"""Trader_7_12 Pro — main launcher.

Read-only market-attention scanner. No order execution and no futures analysis.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from watchlist_ui import WatchlistTraderWindow


def main():
    print("🚀 Запуск Trader_7_12 Pro — Market Attention Radar")

    # Create the Qt application before any backend work and show the window
    # immediately. BCS authorization and scanner construction are deliberately
    # lazy: the dashboard must not depend on a startup network probe or on
    # backend initialization completing before the Qt event loop starts.
    app = QApplication(sys.argv)
    app.setApplicationName("Trader_7_12 Pro")
    app.setQuitOnLastWindowClosed(True)

    window = WatchlistTraderWindow(scanner_enabled=True)
    window.show()
    window.raise_()
    window.activateWindow()

    print(f"🖥️ GUI window visible: {window.isVisible()}")
    print(f"🖥️ GUI platform: {app.platformName()}")

    # Keep scanner initialization inside the GUI lifecycle without blocking
    # the first paint. The actual BCS work remains lazy until a scan starts.
    QTimer.singleShot(0, window._update_session_header)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
