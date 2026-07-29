"""
Trader_7_12 Pro

Main launcher

Версия 0.5

Запуск:
- подключение BCS API
- загрузка рынка
- запуск интерфейса
"""


import sys


from PySide6.QtWidgets import QApplication


from market.market_loader import MarketLoader

from ui import TraderWindow





def main():


    print(
        "🚀 Запуск Trader_7_12 Pro"
    )


    loader = MarketLoader()



    if not loader.connect():

        print(
            "❌ Не удалось подключиться к API БКС"
        )

        return



    market_data = loader.load()



    if market_data is None:

        print(
            "⚠️ Данные рынка не получены"
        )

    else:

        print(
            "✅ Рынок готов"
        )



    app = QApplication(
        sys.argv
    )



    window = TraderWindow()



    window.show()



    sys.exit(
        app.exec()
    )






if __name__ == "__main__":

    main()