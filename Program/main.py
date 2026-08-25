"""
Trader_7_12 Pro

Main launcher

Версия 0.9

Запуск:
- подключение BCS API
- загрузка рынка
- запуск канонического SPOT opportunity watchlist интерфейса

Если BCS временно недоступен, интерфейс всё равно запускается
для просмотра; торговая логика и сканирование не изменяются.
"""

import sys

from PySide6.QtWidgets import QApplication

from market.market_loader import MarketLoader
from watchlist_ui import WatchlistTraderWindow


def main():
    print("🚀 Запуск Trader_7_12 Pro")

    loader = MarketLoader()
    try:
        connected = loader.connect()
    except Exception as exc:
        connected = False
        print(f"⚠️ БКС временно недоступен: {exc}")

    if not connected:
        print("⚠️ Интерфейс запускается в режиме просмотра")
    else:
        print("✅ БКС подключён")
        print("ℹ️ Загрузка рынка будет выполнена только после запуска сканирования")

    app = QApplication(sys.argv)
    window = WatchlistTraderWindow(scanner_enabled=connected)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
