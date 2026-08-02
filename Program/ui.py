"""
Trader_7_12 Pro

UI Module

Версия:
0.6

Изменения:
- подключен MarketData
- получение реальных данных BCS API
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


from market.market_data import MarketData

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


        self.market = MarketData()


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


        self.result_box.setText(
            "📡 Загрузка данных рынка BCS..."
        )


        instruments = self.market.update()



        if not instruments:


            self.result_box.setText(
                "⚠️ Данные рынка отсутствуют"
            )

            return



        results = self.scanner.scan(
            instruments
        )



        output = """

================================

TRADER_7_12 MARKET SCANNER

================================


Получено инструментов:
{}

================================

""".format(
            len(instruments)
        )



        for item in results:


            output += f"""

Инструмент:
{item.get('ticker')}


Цена:
{item.get('price')} ₽


Оборот:
{item.get('money_volume',0):,.0f} ₽


Объем:
{item.get('volume_ratio',0)} x


Рейтинг:
{item.get('volume_score',0)} / 100


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