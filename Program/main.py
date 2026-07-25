import sys

from PySide6.QtWidgets import QApplication

from market.market_loader import MarketLoader
from ui import TraderWindow


def main():

    loader = MarketLoader()

    if not loader.connect():
        print("Не удалось подключиться к API БКС")
        return

    loader.load()

    app = QApplication(sys.argv)

    window = TraderWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()