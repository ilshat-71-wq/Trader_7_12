from datetime import datetime
from zoneinfo import ZoneInfo

from services.moex_price_stability_service import MoexPriceStabilityService


class FakeAPI:
    def __init__(self, bars):
        self.bars = bars

    def get_candles(self, ticker, class_code, interval, start_time, end_time):
        return {"bars": list(self.bars)}


def bar(ts, close, high=None, low=None):
    return {
        "time": ts,
        "open": close,
        "close": close,
        "high": high if high is not None else close,
        "low": low if low is not None else close,
        "volume": 100,
    }


def test_imoex_style_da_threshold_is_detected():
    reference = 100.0
    bars = [
        bar("2026-08-24T07:10:00Z", 79.0, 79.0, 79.0),
        bar("2026-08-24T07:15:00Z", 78.0, 78.0, 78.0),
    ]
    result = MoexPriceStabilityService(FakeAPI(bars)).evaluate(
        "TEST",
        "TQBR",
        reference,
        trading_date=datetime(2026, 8, 24).date(),
        now=datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result["moex_da_trigger_inferred"] is True
    assert result["moex_event_risk"] is True


def test_weekend_three_percent_band_is_detected():
    reference = 100.0
    bars = [
        bar("2026-08-22T07:10:00Z", 103.0, 103.0, 103.0),
    ]
    result = MoexPriceStabilityService(FakeAPI(bars)).evaluate(
        "TEST",
        "TQBR",
        reference,
        trading_date=datetime(2026, 8, 24).date(),
        now=datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result["moex_weekend_band_hit"] is True
    assert result["moex_event_risk"] is True


def test_normal_move_is_not_event_risk():
    reference = 100.0
    bars = [
        bar("2026-08-24T07:10:00Z", 98.0),
        bar("2026-08-24T07:15:00Z", 97.5),
    ]
    result = MoexPriceStabilityService(FakeAPI(bars)).evaluate(
        "TEST",
        "TQBR",
        reference,
        trading_date=datetime(2026, 8, 24).date(),
        now=datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result["moex_event_risk"] is False
