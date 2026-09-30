"""Offline tests for the real-data M1 entry confirmation."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from services.spot_m1_entry_service import SpotM1EntryService


class FakeSession:
    def get_trading_day(self):
        return datetime(2026, 8, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")).date()

    def get_session(self):
        return "MAIN"


class FakeHistory:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    def to_moscow(self, value):
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(self.MOSCOW_TZ)

    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        assert timeframe_minutes == 1
        rows = []
        for minute in range(10):
            volume = 1000 if minute < 9 else 1400
            close = 100.0 if minute < 9 else 101.0
            rows.append({
                "time": f"2026-08-17T{6 + (minute // 60):02d}:{50 + minute:02d}:00Z",
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "money_volume": volume,
            })
        return rows


def test_long_entry_requires_price_and_volume():
    service = SpotM1EntryService(FakeHistory(), FakeSession())
    result = service.analyze(
        "SBER", "TQBR", "LONG", 100.5,
        trading_date=datetime(2026, 8, 17).date(),
        session="MAIN",
        now=datetime(2026, 8, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result["m1_entry_state"] == "CONFIRMED"
    assert result["m1_entry_triggered"] is True
    assert result["m1_volume_state"] == "CONFIRMED"


def test_entry_waits_when_price_has_not_reached_trigger():
    service = SpotM1EntryService(FakeHistory(), FakeSession())
    result = service.analyze(
        "SBER", "TQBR", "SHORT", 99.0,
        trading_date=datetime(2026, 8, 17).date(),
        session="MAIN",
        now=datetime(2026, 8, 17, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )
    assert result["m1_entry_state"] == "WAIT"
    assert result["m1_entry_triggered"] is False


if __name__ == "__main__":
    test_long_entry_requires_price_and_volume()
    test_entry_waits_when_price_has_not_reached_trigger()
    print("ALL TESTS PASSED")
