from services.daily_trend_profile_service import DailyTrendProfileService
from services.market_attention_scanner_service import MarketAttentionScannerService


def _d1_candles():
    rows = []
    close = 100.0
    for day in range(15):
        rows.append({
            "date": f"2026-09-{day + 1:02d}",
            "open": close,
            "high": close + 2.0,
            "low": close - 1.0,
            "close": close + 0.5,
        })
        close += 0.5
    return rows


def test_wilder_atr_uses_only_completed_daily_candles_and_returns_percent():
    candles = _d1_candles()
    atr = DailyTrendProfileService.atr(candles, before_date=__import__("datetime").date(2026, 9, 20), period=14)

    assert atr is not None
    assert atr["period"] == 14
    assert atr["value"] > 0
    assert atr["reference_close"] == candles[-1]["close"]
    assert atr["percent"] == round(atr["value"] / atr["reference_close"] * 100.0, 4)


def test_atr_used_is_session_move_divided_by_real_atr():
    assert MarketAttentionScannerService._atr_used_percent(99.8, 100.0, 2.0) == 10.0
    assert MarketAttentionScannerService._atr_used_percent(100.2, 100.0, 2.0) == 10.0
    assert MarketAttentionScannerService._atr_used_percent(100.0, 100.0, 2.0) == 0.0
    assert MarketAttentionScannerService._atr_used_percent(100.0, 100.0, 0.0) is None
