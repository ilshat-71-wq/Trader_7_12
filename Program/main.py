"""
Trader_7_12 Pro

Main launcher

Версия 0.6

Запуск:
- подключение BCS API
- загрузка рынка
- запуск интерфейса

Если BCS временно недоступен, интерфейс всё равно запускается
для просмотра; торговая логика и сканирование не изменяются.
"""

import sys

from PySide6.QtWidgets import QApplication

from market.market_loader import MarketLoader
from ui import TraderWindow


def main():
    print("🚀 Запуск Trader_7_12 Pro")

    loader = MarketLoader()
    connected = loader.connect()

    if not connected:
        print("⚠️ БКС временно недоступен — интерфейс запускается в режиме просмотра")
    else:
        market_data = loader.load()

        if market_data is None:
            print("⚠️ Данные рынка не получены")
        else:
            print("✅ Рынок готов")

    app = QApplication(sys.argv)
    window = TraderWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
