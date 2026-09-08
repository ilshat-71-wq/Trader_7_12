"""Trader_7_12 Pro — main launcher.

Read-only market-information scanner with futures/OI context. No order execution.
"""

import math
import sys

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QSplashScreen

from oi_watchlist_ui import OIWatchlistTraderWindow


class ScanningSplash(QSplashScreen):
    """Minimal luxury watch-style splash with a moving second hand."""

    def __init__(self):
        size = 520
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        super().__init__(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self._angle = 0.0
        self._size = size
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(40)
        self._redraw()

    def _advance(self):
        self._angle = (self._angle + 2.4) % 360.0
        self._redraw()

    def _redraw(self):
        s = self._size
        pixmap = QPixmap(s, s)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, True)

        bg = QRadialGradient(s * 0.50, s * 0.44, s * 0.55)
        bg.setColorAt(0.0, QColor("#123b3b"))
        bg.setColorAt(0.72, QColor("#071719"))
        bg.setColorAt(1.0, QColor(3, 8, 10, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawEllipse(8, 8, s - 16, s - 16)

        cx, cy = s * 0.50, s * 0.42
        r = s * 0.285
        halo = QRadialGradient(cx, cy, r * 1.28)
        halo.setColorAt(0, QColor(32, 198, 184, 75))
        halo.setColorAt(0.72, QColor(20, 151, 143, 24))
        halo.setColorAt(1, QColor(20, 151, 143, 0))
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), r * 1.28, r * 1.28)

        # Turquoise dial with a restrained gold bezel.
        p.setBrush(QColor("#075e5a"))
        p.setPen(QPen(QColor("#d4af55"), 7))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(QColor("#f0d27a"), 2))
        p.drawEllipse(QPointF(cx, cy), r * 0.92, r * 0.92)

        # Hour markers.
        p.setPen(QPen(QColor("#f1d57d"), 4, Qt.SolidLine, Qt.RoundCap))
        for i in range(12):
            a = math.radians(i * 30 - 90)
            outer = r * 0.84
            inner = r * (0.72 if i % 3 else 0.68)
            p.drawLine(QPointF(cx + math.cos(a) * inner, cy + math.sin(a) * inner),
                       QPointF(cx + math.cos(a) * outer, cy + math.sin(a) * outer))

        # Gold hour/minute hands.
        for angle, length, width in ((126, r * 0.50, 7), (18, r * 0.67, 5)):
            a = math.radians(angle - 90)
            p.setPen(QPen(QColor("#f4d47a"), width, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * length, cy + math.sin(a) * length))

        # Animated second hand and subtle sweep trail.
        a = math.radians(self._angle - 90)
        p.setPen(QPen(QColor(91, 239, 224, 55), 6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a - math.radians(18)) * r * 0.76,
                                           cy + math.sin(a - math.radians(18)) * r * 0.76))
        p.setPen(QPen(QColor("#d9b64f"), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.cos(a) * r * 0.78,
                                           cy + math.sin(a) * r * 0.78))
        p.setBrush(QColor("#f3d477"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), 8, 8)
        p.setBrush(QColor("#075e5a"))
        p.drawEllipse(QPointF(cx, cy), 3, 3)

        p.setPen(QColor("#f0d27a"))
        p.setFont(self.font())
        p.drawText(0, int(s * 0.77), s, 28, Qt.AlignCenter, "TRADER 7_12 PRO")
        p.setPen(QColor("#74d8cf"))
        p.drawText(0, int(s * 0.84), s, 24, Qt.AlignCenter, "MARKET SCANNING")
        p.end()
        self.setPixmap(pixmap)


def main():
    print("🚀 Запуск Trader_7_12 Pro — Market Information Radar")

    app = QApplication(sys.argv)
    app.setApplicationName("Trader_7_12 Pro")
    app.setQuitOnLastWindowClosed(True)

    splash = ScanningSplash()
    splash.show()
    app.processEvents()

    window = OIWatchlistTraderWindow(scanner_enabled=True)
    window.show()
    window.raise_()
    window.activateWindow()

    # Keep the animation visible briefly so the user can immediately see that
    # the application is working; the actual scan continues in the main UI.
    QTimer.singleShot(900, splash.close)
    print(f"🖥️ GUI window visible: {window.isVisible()}")
    print(f"🖥️ GUI platform: {app.platformName()}")

    QTimer.singleShot(0, window._update_session_header)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
