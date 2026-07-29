"""
Trader_7_12 Pro

UI Module

Версия:
0.5

Изменения:
- подключен MarketScanner
- кнопка "Сканировать рынок"
- расчёт вынесен из UI
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


from scanner.market_scanner import MarketScanner




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


        self.scanner = MarketScanner()


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


        # Пока тестовый список
        # Следующим шагом сюда подключим данные BCS API


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



        results = self.scanner.scan(
            instruments
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