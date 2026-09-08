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
    assert "#075e5a" in visual_source
    assert "#d4af55" in visual_source


def test_legacy_three_dial_animation_is_not_selected_by_main():
    root = Path(__file__).resolve().parent
    main_source = (root / "main.py").read_text(encoding="utf-8")
    assert "_draw_clock(p, w * .27" not in main_source
    assert "_draw_clock(p, w * .52" not in main_source
    assert "_draw_clock(p, w * .76" not in main_source
