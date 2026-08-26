from datetime import date, datetime
from zoneinfo import ZoneInfo

from services.spot_first_pullback_service import SpotFirstPullbackService


class FakeHistory:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    def __init__(self, candles): self.candles, self.calls = candles, []
    def to_moscow(self, value):
        if isinstance(value, datetime): return value.astimezone(self.MOSCOW_TZ)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(self.MOSCOW_TZ)
    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        self.calls.append((ticker, class_code, start_time, end_time, timeframe_minutes)); return list(self.candles)


class FakeSession:
    def __init__(self, session): self.session = session
    def get_session(self): return self.session
    def get_trading_day(self): return date(2026, 8, 17)


def candle(minute, open_, high, low, close):
    dt = datetime(2026, 8, 17, 19, minute, tzinfo=ZoneInfo("Europe/Moscow"))
    return {"time": dt.isoformat(), "open": open_, "high": high, "low": low, "close": close, "volume": 100}


def test_long_around_fifty_percent_pullback_becomes_watch():
    candles = [candle(0, 100, 101, 99, 100.8), candle(5, 100.8, 102, 100.7, 101.8), candle(10, 101.8, 102.2, 100.1, 100.9), candle(15, 100.9, 101.1, 100.0, 100.8)]
    result = SpotFirstPullbackService(FakeHistory(candles), FakeSession("EVENING")).analyze("BR", "SPBRU", "LONG")
    assert result["setup"] == "FIRST_PULLBACK" and result["setup_state"] == "WATCH"
    assert 0.35 <= result["retracement_ratio"] <= 0.75 and result["setup_quality_score"] > 60


def test_short_rebound_is_spot_first():
    candles = [candle(0, 100, 100.5, 99, 99.2), candle(5, 99.2, 99.3, 97.5, 98.0), candle(10, 98.0, 99.0, 97.9, 98.7), candle(15, 98.7, 98.9, 98.0, 98.1)]
    result = SpotFirstPullbackService(FakeHistory(candles), FakeSession("EVENING")).analyze("BR", "SPBRU", "SHORT")
    assert result["setup"] == "FIRST_REBOUND" and result["setup_direction"] == "SHORT" and result["setup_state"] == "WATCH"


def test_main_session_uses_main_window():
    history = FakeHistory([candle(0, 100, 101, 99, 100)])
    SpotFirstPullbackService(history, FakeSession("MAIN")).analyze("SBER", "SPBRU", "LONG")
    assert history.calls[0][2].hour == 7
    assert history.calls[0][3].hour == 16
    assert history.calls[0][2].tzinfo == ZoneInfo("UTC")

