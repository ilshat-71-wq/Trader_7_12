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

    # Do not permanently disable the GUI because of a transient startup
    # authorization failure. The scanner owns the same process-wide BCS
    # client and retries authorization when the user starts a scan.
    loader = MarketLoader()
    try:
        connected = loader.connect()
    except Exception as exc:
        connected = False
        print(f"⚠️ Первичная проверка БКС не удалась: {type(exc).__name__}: {exc}")

    print("✅ БКС подключён" if connected else "⚠️ Первичная проверка БКС не пройдена — сканер остаётся доступен")

    app = QApplication(sys.argv)
    window = WatchlistTraderWindow(scanner_enabled=True)
    try:
        window.scanner = MarketAttentionScannerService()
    except Exception as exc:
        print(f"⚠️ Сканер не инициализирован при старте: {type(exc).__name__}: {exc}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
