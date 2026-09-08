"""Premium Trader_7_12 Pro scan-state visual.

The scan animation intentionally reuses the visual language of the application
icon: a single turquoise watch dial, restrained gold bezel and a subtle sweep.
No external image asset is required.
"""

import math

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class PremiumScanVisual(QWidget):
    """Single luxury watch-dial animation shown while the market is scanned."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0.0
        self.setMinimumHeight(360)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self):
        self.phase = 0.0
        self.timer.start(40)
        self.update()

    def stop(self):
        self.timer.stop()

    def _tick(self):
        self.phase = (self.phase + 0.052) % (math.tau)
        self.update()

    def _draw_dial(self, p, cx, cy, r):
        # Soft turquoise aura.
        halo = QRadialGradient(cx, cy, r * 1.55)
        halo.setColorAt(0.0, QColor(40, 220, 205, 62))
        halo.setColorAt(0.48, QColor(22, 174, 164, 28))
        halo.setColorAt(1.0, QColor(22, 174, 164, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), r * 1.55, r * 1.55)

        # Deep premium dial.
        face = QRadialGradient(cx - r * 0.28, cy - r * 0.32, r * 1.25)
        face.setColorAt(0.0, QColor("#0b7771"))
        face.setColorAt(0.62, QColor("#075e5a"))
        face.setColorAt(1.0, QColor("#033d3b"))
        p.setBrush(face)
        p.setPen(QPen(QColor("#d4af55"), max(5.0, r * 0.045)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Double gold bezel.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#f0d27a"), max(1.5, r * 0.012)))
        p.drawEllipse(QPointF(cx, cy), r * 0.91, r * 0.91)
        p.setPen(QPen(QColor(240, 210, 122, 85), max(1.0, r * 0.006)))
        p.drawEllipse(QPointF(cx, cy), r * 0.96, r * 0.96)

        # Twelve refined markers, with stronger quarter markers.
        for i in range(12):
            a = math.radians(i * 30 - 90)
            outer = r * 0.84
            inner = r * (0.70 if i % 3 == 0 else 0.76)
            width = max(3.0, r * (0.025 if i % 3 == 0 else 0.014))
            p.setPen(QPen(QColor("#f2d77f"), width, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx + math.cos(a) * inner, cy + math.sin(a) * inner),
                QPointF(cx + math.cos(a) * outer, cy + math.sin(a) * outer),
            )

        # Subtle inner radial sheen.
        sheen = QRadialGradient(cx - r * 0.22, cy - r * 0.35, r * 0.95)
        sheen.setColorAt(0.0, QColor(105, 242, 228, 24))
        sheen.setColorAt(0.55, QColor(105, 242, 228, 7))
        sheen.setColorAt(1.0, QColor(105, 242, 228, 0))
        p.setBrush(sheen)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 0.88, r * 0.88)

        # Fixed hour/minute hands.
        for degrees, length, width in ((128, 0.48, 0.030), (20, 0.66, 0.021)):
            a = math.radians(degrees - 90)
            p.setPen(QPen(QColor("#f4d47a"), max(4.0, r * width), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx, cy),
                QPointF(cx + math.cos(a) * r * length, cy + math.sin(a) * r * length),
            )

        # Animated gold second hand with a turquoise afterglow.
        a = self.phase - math.pi / 2
        trail_a = a - math.radians(16)
        p.setPen(QPen(QColor(91, 239, 224, 52), max(4.0, r * 0.035), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(trail_a) * r * 0.78, cy + math.sin(trail_a) * r * 0.78),
        )
        p.setPen(QPen(QColor("#d9b64f"), max(2.5, r * 0.016), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(a) * r * 0.79, cy + math.sin(a) * r * 0.79),
        )

        p.setBrush(QColor("#f3d477"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), max(6.0, r * 0.038), max(6.0, r * 0.038))
        p.setBrush(QColor("#075e5a"))
        p.drawEllipse(QPointF(cx, cy), max(2.5, r * 0.014), max(2.5, r * 0.014))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Dark luxury backdrop with a restrained moving light sweep.
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#071719"))
        bg.setColorAt(0.55, QColor("#0b1719"))
        bg.setColorAt(1.0, QColor("#071013"))
        p.fillRect(rect, bg)

        sweep_x = w * (0.5 + 0.43 * math.sin(self.phase * 0.55))
        sweep = QLinearGradient(sweep_x - 180, 0, sweep_x + 180, 0)
        sweep.setColorAt(0.0, QColor(80, 220, 208, 0))
        sweep.setColorAt(0.5, QColor(80, 220, 208, 16))
        sweep.setColorAt(1.0, QColor(80, 220, 208, 0))
        p.fillRect(rect, sweep)

        # Premium single-dial composition.
        cx = w * 0.50
        cy = h * 0.40
        r = min(w, h) * 0.245
        self._draw_dial(p, cx, cy, r)

        # Minimal status typography.
        p.setPen(QColor("#f0d27a"))
        p.setFont(QFont("Helvetica Neue", 13, QFont.Weight.DemiBold))
        p.drawText(rect.adjusted(0, int(h * 0.73), 0, -42), Qt.AlignHCenter | Qt.AlignVCenter, "TRADER 7_12 PRO")

        p.setPen(QColor("#74d8cf"))
        p.setFont(QFont("Helvetica Neue", 11, QFont.Weight.Medium))
        p.drawText(rect.adjusted(0, int(h * 0.80), 0, -21), Qt.AlignHCenter | Qt.AlignVCenter, "MARKET SCANNING")

        p.setPen(QColor("#718b88"))
        p.setFont(QFont("Helvetica Neue", 9))
        p.drawText(rect.adjusted(0, int(h * 0.88), 0, -2), Qt.AlignHCenter | Qt.AlignVCenter, "D1  •  M5  •  RS  •  MONEY FLOW")
        p.end()
