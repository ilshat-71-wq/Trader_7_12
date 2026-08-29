"""
Trader_7_12 Pro

Main launcher

Версия 1.0

Запуск:
- подключение BCS API
- загрузка рынка
- запуск полного opportunity watchlist интерфейса
- SPOT equities + direct macro coverage: OIL/GOLD/GAS/USDRUB

Если BCS временно недоступен, интерфейс всё равно запускается
для просмотра.
"""

import sys

from PySide6.QtWidgets import QApplication

from market.market_loader import MarketLoader
from watchlist_ui import WatchlistTraderWindow
from services.full_market_pipeline_service import FullMarketPipelineService


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
        print("ℹ️ Сканирование включает акции + OIL/GOLD/GAS/USDRUB")

    app = QApplication(sys.argv)
    window = WatchlistTraderWindow(scanner_enabled=connected)
    if connected:
        try:
            window.scanner = FullMarketPipelineService()
        except Exception as exc:
            print(f"⚠️ Полный сканер не инициализирован: {type(exc).__name__}: {exc}")
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
