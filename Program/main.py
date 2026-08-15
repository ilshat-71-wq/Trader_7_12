"""
Trader_7_12 Pro

Main launcher

Версия 0.8

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
    try:
        connected = loader.connect()
    except Exception as exc:
        connected = False
        print(f"⚠️ БКС временно недоступен: {exc}")

    if not connected:
        print("⚠️ Интерфейс запускается в режиме просмотра")
    else:
        try:
            market_data = loader.load()
        except Exception as exc:
            market_data = None
            print(f"⚠️ Не удалось загрузить рынок: {exc}")

        if market_data is None:
            print("⚠️ Данные рынка не получены")
        else:
            print("✅ Рынок готов")

    app = QApplication(sys.argv)
    window = TraderWindow(scanner_enabled=connected)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
