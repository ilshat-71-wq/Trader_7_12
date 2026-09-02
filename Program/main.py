"""Trader_7_12 Pro — main launcher.

Read-only market-attention scanner. No order execution and no futures analysis.
"""

import sys

from PySide6.QtWidgets import QApplication

from market.market_loader import MarketLoader
from watchlist_ui import WatchlistTraderWindow
from services.market_attention_scanner_service import MarketAttentionScannerService


def main():
    print("🚀 Запуск Trader_7_12 Pro — Market Attention Radar")
    loader = MarketLoader()
    try:
        connected = loader.connect()
    except Exception as exc:
        connected = False
        print(f"⚠️ БКС временно недоступен: {exc}")

    print("✅ БКС подключён" if connected else "⚠️ Интерфейс запускается в режиме просмотра")
    app = QApplication(sys.argv)
    window = WatchlistTraderWindow(scanner_enabled=connected)
    if connected:
        try:
            window.scanner = MarketAttentionScannerService()
        except Exception as exc:
            print(f"⚠️ Сканер не инициализирован: {type(exc).__name__}: {exc}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
