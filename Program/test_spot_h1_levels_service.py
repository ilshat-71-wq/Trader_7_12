"""Offline tests for SPOT H1 structural level context."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.spot_first_pullback_service import SpotFirstPullbackService


class FakeSessionService:
    def get_session(self):
        return "MAIN"

    def get_trading_day(self):
        return datetime(2026, 8, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")).date()


class FakeHistoryService:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    def now(self):
        return datetime(2026, 8, 17, 15, 0, tzinfo=self.MOSCOW_TZ)

    def to_moscow(self, value):
        if isinstance(value, str):
            text = value.replace("Z", "+00:00")
            value = datetime.fromisoformat(text)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(self.MOSCOW_TZ)

    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        assert timeframe_minutes == 60
        return [
            {"time": "2026-08-17T06:00:00Z", "open": 99, "high": 101, "low": 98, "close": 100},
            {"time": "2026-08-17T07:00:00Z", "open": 100, "high": 103, "low": 100, "close": 102},
            {"time": "2026-08-17T08:00:00Z", "open": 102, "high": 105, "low": 101, "close": 104},
        ]


def test_long_prefers_near_h1_support():
    service = SpotFirstPullbackService(FakeHistoryService(), FakeSessionService())
    context = service._h1_context("SBER", "TQBR", 101.0)
    assert context["h1_nearest_level_type"] == "SUPPORT"
    assert context["h1_support"] == 101.0
    assert context["h1_level_context"] == "NEAR_H1_SUPPORT"


def test_short_prefers_near_h1_resistance():
    service = SpotFirstPullbackService(FakeHistoryService(), FakeSessionService())
    context = service._h1_context("SBER", "TQBR", 102.8)
    assert context["h1_nearest_level_type"] == "RESISTANCE"
    assert context["h1_resistance"] == 103.0
    assert context["h1_level_context"] == "NEAR_H1_RESISTANCE"


if __name__ == "__main__":
    test_long_prefers_near_h1_support()
    print("PASS test_long_prefers_near_h1_support")
    test_short_prefers_near_h1_resistance()
    print("PASS test_short_prefers_near_h1_resistance")
    print("ALL TESTS PASSED")
