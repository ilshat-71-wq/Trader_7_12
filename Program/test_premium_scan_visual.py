"""Regression tests for the production scan animation."""

from pathlib import Path


def test_premium_scan_visual_is_the_application_scan_widget():
    root = Path(__file__).resolve().parent
    main_source = (root / "main.py").read_text(encoding="utf-8")
    visual_source = (root / "premium_scan_visual.py").read_text(encoding="utf-8")

    assert "from premium_scan_visual import PremiumScanVisual" in main_source
    assert "trader_ui.MeltingClocksWidget = PremiumScanVisual" in main_source
    assert "class PremiumScanVisual(QWidget):" in visual_source
    assert "TRADER 7_12 PRO" in visual_source
    assert "MARKET SCANNING" in visual_source


def test_premium_scan_visual_has_three_real_market_clocks_and_premium_palettes():
    visual_source = (Path(__file__).resolve().parent / "premium_scan_visual.py").read_text(encoding="utf-8")

    assert 'ZoneInfo("Europe/London")' in visual_source
    assert 'ZoneInfo("Europe/Moscow")' in visual_source
    assert 'ZoneInfo("America/New_York")' in visual_source
    assert '"London"' in visual_source
    assert '"Moscow"' in visual_source
    assert '"New-York"' in visual_source
    assert '#b8c8d8' in visual_source  # platinum / royal-blue family
    assert '#b88958' in visual_source  # bronze family
    assert '#d4af55' in visual_source  # existing Moscow gold
    assert 'side_r = center_r * 0.80' in visual_source


def test_legacy_three_dial_animation_is_not_selected_by_main():
    root = Path(__file__).resolve().parent
    main_source = (root / "main.py").read_text(encoding="utf-8")
    assert "_draw_clock(p, w * .27" not in main_source
    assert "_draw_clock(p, w * .52" not in main_source
    assert "_draw_clock(p, w * .76" not in main_source


def test_premium_scan_visual_uses_current_market_session_windows():
    visual_source = (Path(__file__).resolve().parent / "premium_scan_visual.py").read_text(encoding="utf-8")

    assert "session=(6, 50, 23, 50)" in visual_source
    assert "session=(8, 0, 16, 30)" in visual_source
    assert "session=(9, 30, 16, 0)" in visual_source
    assert "start_angle = (start_minutes % (12 * 60)) * 0.5 - 90.0" in visual_source


def test_settings_tab_is_not_covered_by_scan_visual():
    main_source = (Path(__file__).resolve().parent / "main.py").read_text(encoding="utf-8")

    assert "self.market_tabs.currentChanged.connect(self._sync_global_scan_visual)" in main_source
    assert 'return self.market_tabs.tabText(self.market_tabs.currentIndex()).upper() == "SETTINGS"' in main_source
    assert "if self._global_scan_active and not self._settings_tab_active()" in main_source
