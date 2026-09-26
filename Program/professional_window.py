"""Professional shell around the existing Trader_7_12 single-window dashboard.

Keeps the market/OI calculation pipeline untouched. Adds only presentation,
copy workflow, persistent sound settings, and scan audio feedback.
"""

import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from oi_watchlist_ui import OIWatchlistTraderWindow
from morning_radar_ui import MorningRadarWidget
from entry_radar_ui import EntryRadarWidget
from move_radar_ui import MoveRadarWidget
from final_radar_ui import FinalRadarWidget


class ScanSound:
    """Small generated public-domain-style classical motif; no bundled recording."""

    SAMPLE_RATE = 44100

    def __init__(self):
        self._path = None
        self._process = None

    def _ensure_file(self):
        if self._path and Path(self._path).exists():
            return self._path

        root = Path(tempfile.gettempdir()) / "trader_7_12"
        root.mkdir(parents=True, exist_ok=True)
        path = root / "scan_motif.wav"
        if path.exists():
            self._path = str(path)
            return self._path

        # Short synthesized motif using notes from Bach's public-domain Badinerie.
        # It is intentionally a new synthesized rendering, not a commercial recording.
        notes = [
            (783.99, 0.16), (880.00, 0.16), (987.77, 0.16),
            (1046.50, 0.22), (987.77, 0.16), (880.00, 0.16),
            (783.99, 0.16), (698.46, 0.22),
        ]
        frames = []
        for frequency, duration in notes:
            count = int(self.SAMPLE_RATE * duration)
            attack = max(1, int(self.SAMPLE_RATE * 0.012))
            release = max(1, int(self.SAMPLE_RATE * 0.035))
            for i in range(count):
                envelope = min(1.0, i / attack, (count - i) / release)
                sample = math.sin(2.0 * math.pi * frequency * i / self.SAMPLE_RATE)
                sample += 0.22 * math.sin(4.0 * math.pi * frequency * i / self.SAMPLE_RATE)
                value = int(max(-1.0, min(1.0, sample * 0.18 * envelope)) * 32767)
                frames.append(value.to_bytes(2, byteorder="little", signed=True))

        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(self.SAMPLE_RATE)
            audio.writeframes(b"".join(frames))

        self._path = str(path)
        return self._path

    def play(self):
        afplay = shutil.which("afplay")
        if not afplay:
            return
        try:
            self.stop()
            self._process = subprocess.Popen(
                [afplay, "-v", "1.0", self._ensure_file()],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._process = None

    def stop(self):
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._process = None


class ProfessionalTraderWindow(OIWatchlistTraderWindow):
    """Single production window: existing data pipeline + professional controls."""

    def __init__(self, scanner_enabled=True):
        super().__init__(scanner_enabled=scanner_enabled)
        self.settings = QSettings("Trader_7_12", "Trader_7_12 Pro")
        self.sound = ScanSound()
        self.sound_timer = QTimer(self)
        self.sound_timer.timeout.connect(self._play_scan_tick)
        self.sound_enabled = self.settings.value("sound/enabled", True, type=bool)
        self.sound_on_finish = self.settings.value("sound/on_finish", True, type=bool)
        self._configure_professional_tabs()
        self._build_morning_radar_tab()
        self._build_entry_radar_tab()
        self._build_move_radar_tab()
        self._build_final_radar_tab()
        self._build_settings_tab()
        self.morning_radar_refresh_timer = QTimer(self)
        self.morning_radar_refresh_timer.timeout.connect(self._refresh_morning_if_open)
        self.morning_radar_refresh_timer.start(60_000)
        self.session_handoff_timer = QTimer(self)
        self.session_handoff_timer.timeout.connect(self._check_session_handoff)
        self.session_handoff_timer.start(1_000)
        # Always load the persisted morning result once on startup. After 09:00
        # periodic refresh is stopped, but the completed morning snapshot must
        # remain visible when the app is opened later in the day.
        QTimer.singleShot(1200, self.morning_radar.refresh)
        QTimer.singleShot(1300, self._check_session_handoff)

    @staticmethod
    def _moscow_time():
        return datetime.now(ZoneInfo('Europe/Moscow'))

    def _refresh_morning_if_open(self):
        if self._moscow_time().hour < 9:
            self.morning_radar.refresh()

    def _check_session_handoff(self):
        if self._moscow_time().hour < 9:
            return
        self.morning_radar_refresh_timer.stop()
        entry_index = self.market_tabs.indexOf(self.entry_radar)
        if entry_index >= 0:
            self.market_tabs.setCurrentIndex(entry_index)
        self.session_handoff_timer.stop()

    def _configure_professional_tabs(self):
        if self.market_tabs.count() >= 3:
            self.market_tabs.setTabText(0, "RADAR")
            self.market_tabs.setTabText(1, "FUTURES OI")
            self.market_tabs.setTabText(2, "DIAGNOSTICS")
        self.market_tabs.setToolTip("Market → Futures OI → diagnostics → settings")

    def _build_morning_radar_tab(self):
        self.morning_radar = MorningRadarWidget()
        self.market_tabs.addTab(self.morning_radar, "MORNING RADAR")
        self.market_tabs.tabBar().moveTab(self.market_tabs.count() - 1, 1)
        if self.market_tabs.count() >= 4:
            self.market_tabs.setTabText(0, "RADAR")
            self.market_tabs.setTabText(1, "MORNING RADAR")
            self.market_tabs.setTabText(2, "FUTURES OI")
            self.market_tabs.setTabText(3, "DIAGNOSTICS")

    def _build_entry_radar_tab(self):
        self.entry_radar = EntryRadarWidget()
        self.market_tabs.addTab(self.entry_radar, "ENTRY RADAR")
        self.market_tabs.tabBar().moveTab(self.market_tabs.count() - 1, 2)
        for index, title in enumerate(("RADAR", "MORNING RADAR", "ENTRY RADAR", "FUTURES OI", "DIAGNOSTICS")):
            if index < self.market_tabs.count():
                self.market_tabs.setTabText(index, title)

    def _build_move_radar_tab(self):
        self.move_radar = MoveRadarWidget()
        self.market_tabs.addTab(self.move_radar, "MOVE RADAR")
        self.market_tabs.tabBar().moveTab(self.market_tabs.count() - 1, 3)
        for index, title in enumerate((
            "RADAR", "MORNING RADAR", "ENTRY RADAR", "MOVE RADAR", "FUTURES OI", "DIAGNOSTICS"
        )):
            if index < self.market_tabs.count():
                self.market_tabs.setTabText(index, title)

    def _build_final_radar_tab(self):
        self.final_radar = FinalRadarWidget()
        self.market_tabs.addTab(self.final_radar, "FINAL RADAR")
        self.market_tabs.tabBar().moveTab(self.market_tabs.count() - 1, 4)
        for index, title in enumerate((
            "RADAR", "MORNING RADAR", "ENTRY RADAR", "MOVE RADAR",
            "FINAL RADAR", "FUTURES OI", "DIAGNOSTICS"
        )):
            if index < self.market_tabs.count():
                self.market_tabs.setTabText(index, title)

    def _build_settings_tab(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("APP SETTINGS")
        title.setStyleSheet("font-size:16px;font-weight:800;color:#e8ecef;")
        subtitle = QLabel(
            "Settings affect only the interface and notifications. Market calculations are unchanged."
        )
        subtitle.setStyleSheet("font-size:11px;color:#7f8a94;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#20262c;border:1px solid #353e46;border-radius:10px;}"
            "QCheckBox{color:#e6e9ed;font-size:12px;padding:8px;}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        self.sound_checkbox = QCheckBox("Scan sound")
        self.sound_checkbox.setChecked(self.sound_enabled)
        self.sound_checkbox.toggled.connect(self._set_sound_enabled)
        card_layout.addWidget(self.sound_checkbox)

        self.finish_sound_checkbox = QCheckBox("Completion sound")
        self.finish_sound_checkbox.setChecked(self.sound_on_finish)
        self.finish_sound_checkbox.toggled.connect(self._set_finish_sound_enabled)
        card_layout.addWidget(self.finish_sound_checkbox)

        test_row = QHBoxLayout()
        test_button = QPushButton("TEST SOUND")
        test_button.clicked.connect(self.sound.play)
        test_row.addWidget(test_button)
        test_row.addStretch(1)
        card_layout.addLayout(test_row)
        layout.addWidget(card)

        help_text = QLabel(
            "⌘C / Ctrl+C — copy selected table rows.\n"
            "Table context menu — copy selection / entire table / without headers.\n"
            "Sort by clicking a header. Column widths are preserved for the current session."
        )
        help_text.setStyleSheet("font-size:11px;color:#aab3bb;line-height:1.4;")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        layout.addStretch(1)

        self.market_tabs.addTab(panel, "SETTINGS")

    def _set_sound_enabled(self, enabled):
        self.sound_enabled = bool(enabled)
        self.settings.setValue("sound/enabled", self.sound_enabled)
        if not self.sound_enabled:
            self.sound_timer.stop()
            self.sound.stop()

    def _set_finish_sound_enabled(self, enabled):
        self.sound_on_finish = bool(enabled)
        self.settings.setValue("sound/on_finish", self.sound_on_finish)

    def _play_scan_tick(self):
        if self.sound_enabled:
            self.sound.play()

    def run_market_scan(self):
        if self.sound_enabled:
            self.sound.play()
            self.sound_timer.start(8500)
        super().run_market_scan()

    def _stop_scan_sound(self):
        self.sound_timer.stop()
        self.sound.stop()

    def _play_completion_sound(self):
        if not (self.sound_on_finish and self.sound_enabled):
            return
        # Let the Qt event loop finish the UI update before launching afplay.
        # The completion sound belongs to the whole workflow, including Futures OI.
        QTimer.singleShot(300, self.sound.play)

    def _scan_finished(self, results, diagnostics):
        # Radar/SPOT finished. OIWatchlistTraderWindow starts Futures OI here.
        # Do not play the completion sound yet: the full workflow is still running.
        self._stop_scan_sound()
        super()._scan_finished(results, diagnostics)
        if self.oi_thread is None or not self.oi_thread.isRunning():
            self._play_completion_sound()

    def _oi_finished(self, results, diagnostics):
        super()._oi_finished(results, diagnostics)
        self.entry_radar.set_results(getattr(self, "_latest_oi_results", results) or results)
        self._play_completion_sound()

    def _oi_failed(self, error):
        super()._oi_failed(error)
        self._play_completion_sound()

    def _scan_failed(self, error):
        self._stop_scan_sound()
        super()._scan_failed(error)
