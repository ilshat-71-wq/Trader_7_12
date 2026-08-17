"""
Trader_7_12 Pro

Main launcher

Версия 0.8

Запуск:
- подключение BCS API
- запуск интерфейса
- BCS не блокирует запуск UI при временной недоступности
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
        print("✅ БКС подключён")
        print("ℹ️ Загрузка рынка будет выполнена только после запуска сканирования")

    app = QApplication(sys.argv)
    window = TraderWindow(scanner_enabled=connected)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
