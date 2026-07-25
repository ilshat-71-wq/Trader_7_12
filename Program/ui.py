from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from engine import Engine


class TraderWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.engine = Engine()

        self.setWindowTitle("Trader 7-12 Pro")
        self.resize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout()
        central.setLayout(layout)

        # ---------- меню ----------
        menu = QVBoxLayout()

        for text in (
            "📈 Рынок",
            "📋 Сделка",
            "💰 Риск",
            "📒 Журнал",
            "⚙ Настройки",
        ):
            btn = QPushButton(text)
            btn.setMinimumHeight(45)
            menu.addWidget(btn)

        menu.addStretch()

        # ---------- рабочая область ----------
        work = QVBoxLayout()

        title = QLabel("Trader 7–12 Pro")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:28px;font-weight:bold;")

        status = QLabel("🟡 ОЖИДАНИЕ")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("font-size:22px;color:orange;")

        self.clock = QLabel()
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setStyleSheet("font-size:15px;color:gray;")

        self.market = QLabel()
        self.market.setStyleSheet("font-size:17px;")

        work.addWidget(title)
        work.addWidget(status)
        work.addWidget(self.clock)
        work.addSpacing(20)
        work.addWidget(self.market)
        work.addStretch()

        layout.addLayout(menu, 1)
        layout.addLayout(work, 4)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_screen)
        self.timer.start(1000)

        self.update_screen()

    def update_screen(self):

        self.engine.update()

        now = datetime.now().strftime("%d.%m.%Y   %H:%M:%S")
        self.clock.setText(now)

        data = self.engine.get_market()

        text = ""

        for symbol, item in data.items():

            text += (
                f"{symbol}\n"
                f"Цена: {item['price']}\n"
                f"Объем: {item['volume']:,}\n"
                f"Цена × Объем: {item['turnover']:,.0f}\n\n"
            )

        self.market.setText(text)