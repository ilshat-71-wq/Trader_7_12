from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from services.spot_first_pullback_service import SpotFirstPullbackService


class FakeHistory:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    def __init__(self, candles):
        self.candles = candles
        self.calls = []

    def to_moscow(self, value):
        if isinstance(value, datetime):
            return value.astimezone(self.MOSCOW_TZ)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(self.MOSCOW_TZ)

    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        self.calls.append((ticker, class_code, start_time, end_time, timeframe_minutes))
        return list(self.candles)


class FakeSession:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return self.session

    def get_trading_day(self):
        return date(2026, 8, 17)


def candle(minute, open_, high, low, close):
    dt = datetime(2026, 8, 17, 19, minute, tzinfo=ZoneInfo("Europe/Moscow"))
    return {"time": dt.isoformat(), "open": open_, "high": high, "low": low, "close": close, "volume": 100}


def test_long_around_fifty_percent_pullback_becomes_watch():
    candles = [
        candle(0, 100, 101, 99, 100.8),
        candle(5, 100.8, 102, 100.7, 101.8),
        candle(10, 101.8, 102.2, 100.1, 100.9),
        candle(15, 100.9, 101.1, 100.0, 100.8),
    ]
    service = SpotFirstPullbackService(FakeHistory(candles), FakeSession("EVENING"))
    result = service.analyze("BR", "SPBRU", "LONG")
    assert result["setup"] == "FIRST_PULLBACK"
    assert result["setup_state"] == "WATCH"
    assert 0.35 <= result["retracement_ratio"] <= 0.75
    assert result["setup_quality_score"] > 60


def test_short_rebound_is_spot_first():
    candles = [
        candle(0, 100, 100.5, 99, 99.2),
        candle(5, 99.2, 99.3, 97.5, 98.0),
        candle(10, 98.0, 99.0, 97.9, 98.7),
        candle(15, 98.7, 98.9, 98.0, 98.1),
    ]
    service = SpotFirstPullbackService(FakeHistory(candles), FakeSession("EVENING"))
    result = service.analyze("BR", "SPBRU", "SHORT")
    assert result["setup"] == "FIRST_REBOUND"
    assert result["setup_direction"] == "SHORT"
    assert result["setup_state"] == "WATCH"


def test_main_session_uses_main_window():
    candles = [candle(0, 100, 101, 99, 100)]
    history = FakeHistory(candles)
    service = SpotFirstPullbackService(history, FakeSession("MAIN"))
    service.analyze("SBER", "SPBRU", "LONG")
    assert history.calls[0][2].hour == 10
    assert history.calls[0][3].hour == 19


def run_tests():
    tests = [
        test_long_around_fifty_percent_pullback_becomes_watch,
        test_short_rebound_is_spot_first,
        test_main_session_uses_main_window,
    ]
    for test in tests:
        test()
        print("PASS", test.__name__)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run_tests()
