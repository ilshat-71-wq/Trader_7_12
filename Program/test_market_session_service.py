from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_session_service import MarketSessionService


SERVICE = MarketSessionService()
MSK = ZoneInfo("Europe/Moscow")


def test_session_boundaries():
    assert SERVICE.get_session(datetime(2026, 8, 17, 6, 59, tzinfo=MSK)) == "PRE_OPEN"
    assert SERVICE.get_session(datetime(2026, 8, 17, 7, 0, tzinfo=MSK)) == "MORNING"
    assert SERVICE.get_session(datetime(2026, 8, 17, 9, 59, 59, tzinfo=MSK)) == "MORNING"
    assert SERVICE.get_session(datetime(2026, 8, 17, 10, 0, tzinfo=MSK)) == "MAIN"
    assert SERVICE.get_session(datetime(2026, 8, 17, 18, 59, 59, tzinfo=MSK)) == "MAIN"
    assert SERVICE.get_session(datetime(2026, 8, 17, 19, 0, tzinfo=MSK)) == "EVENING"
    assert SERVICE.get_session(datetime(2026, 8, 17, 23, 49, 59, tzinfo=MSK)) == "EVENING"
    assert SERVICE.get_session(datetime(2026, 8, 17, 23, 50, tzinfo=MSK)) == "CLOSED"


def test_session_info_contains_live_clock_fields():
    value = datetime(2026, 8, 17, 19, 15, 30, tzinfo=MSK)
    info = SERVICE.get_session_info(value)
    assert info["session"] == "EVENING"
    assert info["label"] == "ВЕЧЕРНЯЯ СЕССИЯ"
    assert info["date"] == "2026-08-17"
    assert info["time"] == "19:15:30"
    assert info["market_open"] is True


def test_utc_datetime_is_converted_to_moscow():
    value = datetime(2026, 8, 17, 16, 15, tzinfo=ZoneInfo("UTC"))
    assert SERVICE.get_session(value) == "MAIN"


if __name__ == "__main__":
    for test in (test_session_boundaries, test_session_info_contains_live_clock_fields, test_utc_datetime_is_converted_to_moscow):
        test()
        print("PASS", test.__name__)
    print("ALL TESTS PASSED")
