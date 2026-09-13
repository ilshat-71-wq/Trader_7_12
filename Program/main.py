"""Trader_7_12 Pro — main launcher.

Read-only market-information scanner with futures/OI context. No order execution.
"""

import math
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QApplication, QSplashScreen

# The production app uses one premium scan visual across the UI.  Patch the
# legacy widget name before the dashboard is imported so the old animation
# cannot be instantiated by the application.
import ui as trader_ui
from premium_scan_visual import PremiumScanVisual

trader_ui.MeltingClocksWidget = PremiumScanVisual

from professional_window import ProfessionalTraderWindow


MOSCOW_TZ = ZoneInfo("Europe/Moscow")


class ScanningSplash(QSplashScreen):
    """Startup splash with a real-time Moscow clock and animated sweep."""

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

    @staticmethod
    def _moscow_time():
        return datetime.now(MOSCOW_TZ)

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

        p.setBrush(QColor("#075e5a"))
        p.setPen(QPen(QColor("#d4af55"), 7))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(QColor("#f0d27a"), 2))
        p.drawEllipse(QPointF(cx, cy), r * 0.92, r * 0.92)

        p.setPen(QPen(QColor("#f1d57d"), 4, Qt.SolidLine, Qt.RoundCap))
        for i in range(12):
            a = math.radians(i * 30 - 90)
            outer = r * 0.84
            inner = r * (0.72 if i % 3 else 0.68)
            p.drawLine(
                QPointF(cx + math.cos(a) * inner, cy + math.sin(a) * inner),
                QPointF(cx + math.cos(a) * outer, cy + math.sin(a) * outer),
            )

        # Real Moscow time: the startup clock is no longer a static illustration.
        now = self._moscow_time()
        seconds = now.second + now.microsecond / 1_000_000.0
        minutes = now.minute + seconds / 60.0
        hours = (now.hour % 12) + minutes / 60.0

        for angle, length, width in (
            (hours * 30.0 - 90.0, 0.50, 7),
            (minutes * 6.0 - 90.0, 0.67, 5),
        ):
            a = math.radians(angle)
            p.setPen(QPen(QColor("#f4d47a"), width, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx, cy),
                QPointF(cx + math.cos(a) * r * length, cy + math.sin(a) * r * length),
            )

        a = math.radians(seconds * 6.0 - 90.0)
        p.setPen(QPen(QColor(91, 239, 224, 55), 6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(a - math.radians(18)) * r * 0.76,
                     cy + math.sin(a - math.radians(18)) * r * 0.76),
        )
        p.setPen(QPen(QColor("#d9b64f"), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(a) * r * 0.78,
                     cy + math.sin(a) * r * 0.78),
        )
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
        p.setPen(QColor("#f0d27a"))
        p.drawText(0, int(s * 0.90), s, 22, Qt.AlignCenter, f"MSK  {now:%H:%M:%S}")
        p.end()
        self.setPixmap(pixmap)


class ScanVisualTraderWindow(ProfessionalTraderWindow):
    """Keep the same premium watch visible over every tab while any scan runs."""

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.global_scan_visual = PremiumScanVisual(self.market_tabs)
        self.global_scan_visual.hide()
        self._position_global_scan_visual()

    def _position_global_scan_visual(self):
        if not hasattr(self, "global_scan_visual"):
            return
        tab_bar = self.market_tabs.tabBar()
        top = tab_bar.geometry().bottom() + 1
        width = max(1, self.market_tabs.width() - 2)
        height = max(1, self.market_tabs.height() - top - 2)
        self.global_scan_visual.setGeometry(1, top, width, height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_global_scan_visual()

    def _show_global_scan_visual(self):
        self._position_global_scan_visual()
        self.global_scan_visual.show()
        self.global_scan_visual.raise_()
        self.global_scan_visual.start()

    def _hide_global_scan_visual(self):
        self.global_scan_visual.stop()
        self.global_scan_visual.hide()

    def _start_scan_animation(self):
        super()._start_scan_animation()
        self.result_stack.setCurrentWidget(self.result_panel)
        self._show_global_scan_visual()

    def _stop_scan_animation(self):
        super()._stop_scan_animation()
        self._hide_global_scan_visual()

    def _start_oi_scan(self):
        self._show_global_scan_visual()
        super()._start_oi_scan()

    def _oi_finished(self, results, diagnostics):
        self._hide_global_scan_visual()
        super()._oi_finished(results, diagnostics)

    def _oi_failed(self, error):
        self._hide_global_scan_visual()
        super()._oi_failed(error)


def main():
    print("🚀 Запуск Trader_7_12 Pro — Market Information Radar")

    app = QApplication(sys.argv)
    app.setApplicationName("Trader_7_12 Pro")
    app.setOrganizationName("Trader_7_12")
    app.setQuitOnLastWindowClosed(True)

    splash = ScanningSplash()
    splash.show()
    app.processEvents()

    window = ScanVisualTraderWindow(scanner_enabled=True)
    window.show()
    window.raise_()
    window.activateWindow()

    QTimer.singleShot(900, splash.close)
    print(f"🖥️ GUI window visible: {window.isVisible()}")
    print(f"🖥️ GUI platform: {app.platformName()}")

    QTimer.singleShot(0, window._update_session_header)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
