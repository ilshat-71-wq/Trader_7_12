"""Premium Trader_7_12 Pro scan-state visual.

A single scan-state composition built from three coordinated luxury watch dials.
Moscow remains the hero dial and keeps the original turquoise/gold language.
London and New-York use restrained royal-blue/platinum and bronze/graphite palettes.
All three clocks show real local wall time and the visual exists only while scanning.
"""

import math
from datetime import datetime, time
from zoneinfo import ZoneInfo

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
LONDON_TZ = ZoneInfo("Europe/London")
NEW_YORK_TZ = ZoneInfo("America/New_York")


class PremiumScanVisual(QWidget):
    """Three coordinated luxury clocks shown while the market is scanned."""

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
        self.phase = (self.phase + 0.052) % math.tau
        self.update()

    @staticmethod
    def _now(tz):
        return datetime.now(tz)

    @staticmethod
    def _session_state(now, start_hour, start_minute, end_hour, end_minute):
        """Return progress and active state for the visual session arc."""
        start = start_hour * 60 + start_minute
        end = end_hour * 60 + end_minute
        current = now.hour * 60 + now.minute + now.second / 60.0
        if end <= start:
            end += 24 * 60
        probe = current
        if probe < start:
            probe += 24 * 60
        active = start <= probe <= end
        progress = max(0.0, min(1.0, (probe - start) / (end - start)))
        return progress, active

    def _draw_session_ring(self, p, cx, cy, r, color, progress, active, width):
        # Thin metallic outer ring: the current trading-session position.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 58), width * 0.48))
        p.drawEllipse(QPointF(cx, cy), r * 1.045, r * 1.045)

        if active:
            glow = QColor(color.red(), color.green(), color.blue(), 42)
            p.setPen(QPen(glow, width * 1.55))
            p.drawArc(
                int(cx - r * 1.045), int(cy - r * 1.045),
                int(r * 2.09), int(r * 2.09),
                90 * 16, -int(360 * progress * 16),
            )

        p.setPen(QPen(color, width))
        p.drawArc(
            int(cx - r * 1.045), int(cy - r * 1.045),
            int(r * 2.09), int(r * 2.09),
            90 * 16, -int(360 * progress * 16),
        )

    def _draw_dial(self, p, cx, cy, r, *, name, tz, palette, session):
        bezel, face0, face1, face2, marker, hand, second, halo = palette

        # Soft, restrained aura matching the metal of the individual watch.
        aura = QRadialGradient(cx, cy, r * 1.55)
        aura.setColorAt(0.0, QColor(halo.red(), halo.green(), halo.blue(), 48))
        aura.setColorAt(0.52, QColor(halo.red(), halo.green(), halo.blue(), 18))
        aura.setColorAt(1.0, QColor(halo.red(), halo.green(), halo.blue(), 0))
        p.setPen(Qt.NoPen)
        p.setBrush(aura)
        p.drawEllipse(QPointF(cx, cy), r * 1.55, r * 1.55)

        # Deep, velvet-like dial.
        face = QRadialGradient(cx - r * 0.27, cy - r * 0.31, r * 1.25)
        face.setColorAt(0.0, face0)
        face.setColorAt(0.58, face1)
        face.setColorAt(1.0, face2)
        p.setBrush(face)
        p.setPen(QPen(bezel, max(4.0, r * 0.045)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Layered metallic bezel.
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(marker, max(1.4, r * 0.012)))
        p.drawEllipse(QPointF(cx, cy), r * 0.91, r * 0.91)
        p.setPen(QPen(QColor(marker.red(), marker.green(), marker.blue(), 72), max(1.0, r * 0.006)))
        p.drawEllipse(QPointF(cx, cy), r * 0.96, r * 0.96)

        # Trading-session radius.
        now = self._now(tz)
        progress, active = self._session_state(now, *session)
        self._draw_session_ring(p, cx, cy, r, marker, progress, active, max(2.0, r * 0.012))

        # Refined hour markers.
        for i in range(12):
            a = math.radians(i * 30 - 90)
            outer = r * 0.84
            inner = r * (0.69 if i % 3 == 0 else 0.76)
            marker_width = max(3.0, r * (0.025 if i % 3 == 0 else 0.014))
            p.setPen(QPen(marker, marker_width, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx + math.cos(a) * inner, cy + math.sin(a) * inner),
                QPointF(cx + math.cos(a) * outer, cy + math.sin(a) * outer),
            )

        # Subtle glass sheen.
        sheen = QRadialGradient(cx - r * 0.22, cy - r * 0.35, r * 0.95)
        sheen.setColorAt(0.0, QColor(255, 255, 255, 19))
        sheen.setColorAt(0.55, QColor(255, 255, 255, 6))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(sheen)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), r * 0.88, r * 0.88)

        # Real local wall-clock time with fractional seconds.
        seconds = now.second + now.microsecond / 1_000_000.0
        minutes = now.minute + seconds / 60.0
        hours = (now.hour % 12) + minutes / 60.0
        hour_angle = hours * 30.0 - 90.0
        minute_angle = minutes * 6.0 - 90.0
        second_angle = seconds * 6.0 - 90.0

        for angle, length, hand_width in (
            (hour_angle, 0.48, 0.030),
            (minute_angle, 0.66, 0.021),
        ):
            a = math.radians(angle)
            p.setPen(QPen(hand, max(3.0, r * hand_width), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(
                QPointF(cx, cy),
                QPointF(cx + math.cos(a) * r * length, cy + math.sin(a) * r * length),
            )

        # Second hand: delicate metal with a restrained trailing glow.
        a = math.radians(second_angle)
        trail_a = a - math.radians(16)
        p.setPen(QPen(QColor(second.red(), second.green(), second.blue(), 46), max(3.0, r * 0.032), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(trail_a) * r * 0.77, cy + math.sin(trail_a) * r * 0.77),
        )
        p.setPen(QPen(second, max(2.2, r * 0.016), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(a) * r * 0.79, cy + math.sin(a) * r * 0.79),
        )

        p.setBrush(marker)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), max(5.0, r * 0.038), max(5.0, r * 0.038))
        p.setBrush(face1)
        p.drawEllipse(QPointF(cx, cy), max(2.0, r * 0.014), max(2.0, r * 0.014))

        return now

    def _draw_label(self, p, x, y, name, time_text, accent, scale=1.0):
        p.setPen(accent)
        p.setFont(QFont("Helvetica Neue", max(9, int(11 * scale)), QFont.Weight.DemiBold))
        p.drawText(int(x - 90 * scale), int(y), int(180 * scale), 18, Qt.AlignCenter, name)
        p.setPen(QColor(accent.red(), accent.green(), accent.blue(), 175))
        p.setFont(QFont("Helvetica Neue", max(8, int(9 * scale)), QFont.Weight.Medium))
        p.drawText(int(x - 90 * scale), int(y + 17), int(180 * scale), 16, Qt.AlignCenter, time_text)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        w, h = rect.width(), rect.height()

        # Existing dark luxury backdrop remains unchanged in spirit.
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

        # Moscow remains the visual hero. Side dials are deliberately one tier smaller.
        center_y = h * 0.36
        side_y = center_y + h * 0.055
        center_r = min(w, h) * 0.245
        side_r = center_r * 0.80

        london_palette = (
            QColor("#b8c8d8"),  # bezel / platinum
            QColor("#142b49"),  # face highlight
            QColor("#0b1d34"),  # face body
            QColor("#071322"),  # face edge
            QColor("#8fa9c2"),  # markers
            QColor("#d9e4ee"),  # hands
            QColor("#86a8c8"),  # second hand
            QColor("#274f78"),  # halo
        )
        moscow_palette = (
            QColor("#d4af55"),
            QColor("#0b7771"),
            QColor("#075e5a"),
            QColor("#033d3b"),
            QColor("#f2d77f"),
            QColor("#f4d47a"),
            QColor("#d9b64f"),
            QColor("#22b9ae"),
        )
        new_york_palette = (
            QColor("#b88958"),  # bronze bezel
            QColor("#3a2920"),  # warm graphite highlight
            QColor("#211b18"),  # velvet graphite
            QColor("#100f0e"),  # deep edge
            QColor("#d1a879"),  # markers
            QColor("#ead4b6"),  # hands
            QColor("#c99a67"),  # second hand
            QColor("#754e32"),  # halo
        )

        london_now = self._draw_dial(
            p, w * 0.25, side_y, side_r,
            name="London", tz=LONDON_TZ, palette=london_palette,
            session=(8, 0, 16, 30),
        )
        moscow_now = self._draw_dial(
            p, w * 0.50, center_y, center_r,
            name="Moscow", tz=MOSCOW_TZ, palette=moscow_palette,
            session=(7, 0, 23, 50),
        )
        new_york_now = self._draw_dial(
            p, w * 0.75, side_y, side_r,
            name="New-York", tz=NEW_YORK_TZ, palette=new_york_palette,
            session=(9, 30, 16, 0),
        )

        # City names and real local times sit directly below their respective dials.
        self._draw_label(p, w * 0.25, side_y + side_r + 12, "London", london_now.strftime("%H:%M:%S"), QColor("#b8c8d8"), 0.90)
        self._draw_label(p, w * 0.50, center_y + center_r + 14, "Moscow", moscow_now.strftime("%H:%M:%S"), QColor("#f0d27a"), 1.0)
        self._draw_label(p, w * 0.75, side_y + side_r + 12, "New-York", new_york_now.strftime("%H:%M:%S"), QColor("#cda67a"), 0.90)

        # Existing scan-state typography remains at the bottom of the widget.
        p.setPen(QColor("#f0d27a"))
        p.setFont(QFont("Helvetica Neue", 13, QFont.Weight.DemiBold))
        p.drawText(rect.adjusted(0, int(h * 0.77), 0, -40), Qt.AlignHCenter | Qt.AlignVCenter, "TRADER 7_12 PRO")

        p.setPen(QColor("#74d8cf"))
        p.setFont(QFont("Helvetica Neue", 11, QFont.Weight.Medium))
        p.drawText(rect.adjusted(0, int(h * 0.825), 0, -20), Qt.AlignHCenter | Qt.AlignVCenter, "MARKET SCANNING")

        p.setPen(QColor("#718b88"))
        p.setFont(QFont("Helvetica Neue", 9))
        p.drawText(rect.adjusted(0, int(h * 0.91), 0, 0), Qt.AlignHCenter | Qt.AlignVCenter, "D1  •  M5  •  RS  •  MONEY FLOW")
        p.end()
