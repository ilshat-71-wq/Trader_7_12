from datetime import date

from services.daily_trend_profile_service import DailyTrendProfileService


def candle(day, o, h, l, c):
    return {"time": f"{day}T00:00:00Z", "open": o, "high": h, "low": l, "close": c}


def test_three_green_rising_structure_and_daily_outperformance_is_long():
    asset = [candle("2026-08-28", 100, 104, 99, 103), candle("2026-08-31", 103, 107, 102, 106), candle("2026-09-01", 106, 110, 105, 109)]
    market = [candle("2026-08-28", 100, 103, 99, 102), candle("2026-08-31", 102, 104, 101, 103), candle("2026-09-01", 103, 105, 102, 104)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["direction"] == "LONG"
    assert result["structure_state"] == "STRONG_STRUCTURE"
    assert result["relative_direction"] == "STRONGER"
    assert result["relative_consistent"] is True


def test_three_red_falling_structure_and_daily_underperformance_is_short():
    asset = [candle("2026-08-28", 110, 111, 106, 107), candle("2026-08-31", 107, 108, 102, 103), candle("2026-09-01", 103, 104, 98, 99)]
    market = [candle("2026-08-28", 110, 111, 108, 109), candle("2026-08-31", 109, 110, 107, 108), candle("2026-09-01", 108, 109, 105, 107)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["direction"] == "SHORT"
    assert result["structure_state"] == "WEAK_STRUCTURE"
    assert result["relative_direction"] == "WEAKER"


def test_mixed_candles_do_not_qualify():
    asset = [candle("2026-08-28", 100, 104, 99, 103), candle("2026-08-31", 103, 107, 102, 102), candle("2026-09-01", 102, 110, 101, 109)]
    market = [candle("2026-08-28", 100, 103, 99, 102), candle("2026-08-31", 102, 104, 101, 103), candle("2026-09-01", 103, 105, 102, 104)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["direction"] == "NEUTRAL"
    assert result["qualified"] is False


def test_strong_structure_with_mixed_daily_rs_does_not_qualify():
    asset = [candle("2026-08-28", 100, 104, 99, 103), candle("2026-08-31", 103, 107, 102, 106), candle("2026-09-01", 106, 110, 105, 109)]
    market = [candle("2026-08-28", 100, 103, 99, 102), candle("2026-08-31", 102, 104, 101, 105), candle("2026-09-01", 105, 108, 104, 108)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["structure_direction"] == "LONG"
    assert result["relative_direction"] == "MIXED"
    assert result["direction"] == "NEUTRAL"


def test_current_incomplete_day_is_excluded():
    asset = [candle("2026-08-31", 100, 104, 99, 103), candle("2026-09-01", 103, 107, 102, 106), candle("2026-09-02", 106, 130, 105, 129)]
    market = [candle("2026-08-31", 100, 103, 99, 102), candle("2026-09-01", 102, 104, 101, 103), candle("2026-09-02", 103, 120, 102, 119)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["days"] == 2
    assert result["return_percent"] < 10


def test_daily_rs_aligns_by_date_not_array_position():
    asset = [candle("2026-08-31", 100, 104, 99, 103), candle("2026-09-01", 103, 107, 102, 106)]
    market = [candle("2026-09-01", 100, 101, 99, 99), candle("2026-08-31", 100, 101, 99, 100)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["relative_consistent"] is True
    assert [x["date"] for x in result["daily_relative"]] == ["2026-08-31", "2026-09-01"]


def test_insufficient_d1_data_is_neutral():
    asset = [candle("2026-09-01", 100, 101, 99, 100)]
    market = [candle("2026-09-01", 100, 101, 99, 100)]
    result = DailyTrendProfileService.analyze(asset, market, before_date=date(2026, 9, 2))
    assert result["direction"] == "NEUTRAL"
    assert result["qualified"] is False
