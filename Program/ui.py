"""
Trader_7_12 Pro

UI Module

Версия:
0.4

Изменения:
- добавлена кнопка "Сканировать рынок"
- подготовлено подключение сканера
"""


from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QTextEdit
)

from PySide6.QtCore import Qt


# Пока используем Volume x Price напрямую
# На следующем шаге заменим на market_scanner.py

from scanner.volume_price import analyze_volume



class TraderWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "Trader_7_12 Pro"
        )

        self.resize(
            900,
            600
        )

        self.init_ui()



    def init_ui(self):

        self.title = QLabel(
            "TRADER_7_12 PRO"
        )

        self.title.setAlignment(
            Qt.AlignCenter
        )


        self.scan_button = QPushButton(
            "Сканировать рынок"
        )


        self.scan_button.clicked.connect(
            self.run_market_scan
        )


        self.result_box = QTextEdit()

        self.result_box.setReadOnly(
            True
        )


        layout = QVBoxLayout()


        layout.addWidget(
            self.title
        )


        layout.addWidget(
            self.scan_button
        )


        layout.addWidget(
            self.result_box
        )


        self.setLayout(
            layout
        )



    def run_market_scan(self):

        # Временно тестовые данные
        # На следующем шаге сюда подключим market_scanner.py

        instruments = [

            {
                "ticker": "SBER-9.26",
                "price": 34500,
                "volume": 150000,
                "average_volume": 60000
            },

            {
                "ticker": "Si-9.26",
                "price": 92000,
                "volume": 80000,
                "average_volume": 70000
            },

            {
                "ticker": "BR-9.26",
                "price": 68000,
                "volume": 120000,
                "average_volume": 40000
            }

        ]


        results = []


        for item in instruments:

            result = analyze_volume(

                ticker=item["ticker"],

                price=item["price"],

                volume=item["volume"],

                average_volume=item["average_volume"]

            )

            results.append(
                result
            )



        results.sort(

            key=lambda x: x["volume_score"],

            reverse=True

        )



        output = """

================================

TRADER_7_12 MARKET SCANNER

================================

"""


        for item in results:


            output += f"""

Инструмент:
{item['ticker']}


Цена:
{item['price']} ₽


Оборот:
{item['money_volume']:,.0f} ₽


Объем:
{item['volume_ratio']} x


Рейтинг:
{item['volume_score']} / 100


------------------------------

"""


        self.result_box.setText(
            output
        )





if __name__ == "__main__":


    app = QApplication([])


    window = TraderWindow()


    window.show()


    app.exec()