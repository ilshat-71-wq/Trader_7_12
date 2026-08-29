"""Deterministic tests for the 2/3/4-day daily SPOT trend profile."""

from services.daily_trend_profile_service import DailyTrendProfileService


def candle(close):
    return {"close": close}


def test_persistent_long_across_2_3_4_days():
    candles = [candle(100), candle(101), candle(103), candle(105), candle(107)]
    result = DailyTrendProfileService.analyze(candles)

    assert result["direction"] == "LONG"
    assert result["alignment_percent"] == 100.0
    assert result["persistent_windows"] == 3
    assert result["windows"]["2"]["state"] == "PERSISTENT"
    assert result["windows"]["3"]["state"] == "PERSISTENT"
    assert result["windows"]["4"]["state"] == "PERSISTENT"


def test_persistent_short_across_2_3_4_days():
    candles = [candle(107), candle(105), candle(103), candle(101), candle(100)]
    result = DailyTrendProfileService.analyze(candles)

    assert result["direction"] == "SHORT"
    assert result["alignment_percent"] == 100.0
    assert result["persistent_windows"] == 3


def test_mixed_daily_structure_is_not_called_persistent():
    # Last four closes: 100 -> 110 -> 100 -> 100.
    # A short 3-day window sees a reversal, but the 2-day and 4-day windows
    # do not confirm it. The aggregate must therefore remain neutral.
    candles = [candle(100), candle(100), candle(110), candle(100), candle(100)]
    result = DailyTrendProfileService.analyze(candles)

    assert result["direction"] == "NEUTRAL"
    assert result["persistent_windows"] == 0
    assert result["windows"]["4"]["state"] == "MIXED"


def test_single_window_impulse_cannot_create_aggregate_short():
    candles = [candle(100), candle(100), candle(110), candle(100)]
    result = DailyTrendProfileService.analyze(candles)

    assert result["windows"]["3"]["direction"] == "SHORT"
    assert result["windows"]["4"]["direction"] == "NEUTRAL"
    assert result["direction"] == "NEUTRAL"


def test_insufficient_history_is_explicit():
    result = DailyTrendProfileService.analyze([candle(100), candle(101), candle(102)])

    assert result["windows"]["2"]["state"] == "PERSISTENT"
    assert result["windows"]["3"]["state"] == "PERSISTENT"
    assert result["windows"]["4"]["state"] == "INSUFFICIENT_DATA"
