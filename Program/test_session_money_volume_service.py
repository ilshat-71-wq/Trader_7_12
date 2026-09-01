"""Tests for current-session SPOT money volume and recent activity."""

from datetime import datetime
from zoneinfo import ZoneInfo

from services.session_money_volume_service import SessionMoneyVolumeService


MSK = ZoneInfo("Europe/Moscow")


class FakeSessionService:
    def __init__(self, dt):
        self.dt = dt

    def now(self):
        return self.dt

    def get_session(self):
        return "EVENING"

    def get_trading_day(self):
        return self.dt.date()


class FakeHistoryService:
    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        return [
            {"time": "2026-08-17T16:05:00Z", "money_volume": 100_000},
            {"time": "2026-08-17T16:10:00Z", "money_volume": 200_000},
            {"time": "2026-08-17T16:15:00Z", "money_volume": 300_000},
        ]


def test_evening_window():
    service = SessionMoneyVolumeService(
        history_service=FakeHistoryService(),
        session_service=FakeSessionService(datetime(2026, 8, 17, 20, 0, tzinfo=MSK)),
    )
    result = service.calculate("BR", "SPBRU", session="EVENING")
    assert result["session"] == "EVENING"
    assert result["money_volume"] == 600_000
    assert result["elapsed_minutes"] == 60
    assert result["expected_minutes"] == 290
    assert result["recent_money_volume"] == 600_000
    assert result["recent_money_per_minute"] == 10_000
    assert result["recent_money_minutes"] == 15


def test_closed_session_returns_zero():
    service = SessionMoneyVolumeService(
        history_service=FakeHistoryService(),
        session_service=FakeSessionService(datetime(2026, 8, 17, 23, 55, tzinfo=MSK)),
    )
    result = service.calculate("BR", "SPBRU", session="CLOSED")
    assert result["money_volume"] == 0.0
    assert result["elapsed_minutes"] == 0
    assert result["recent_money_volume"] == 0.0


if __name__ == "__main__":
    test_evening_window()
    print("PASS test_evening_window")
    test_closed_session_returns_zero()
    print("PASS test_closed_session_returns_zero")
    print("ALL TESTS PASSED")
