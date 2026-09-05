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


def test_weekend_additional_session_is_open():
    saturday = datetime(2026, 9, 5, 10, 44, tzinfo=MSK)
    assert SERVICE.get_session(saturday) == "WEEKEND_SESSION"
    assert SERVICE.get_session_label(saturday) == "ДОПОЛНИТЕЛЬНАЯ СЕССИЯ ВЫХОДНОГО ДНЯ"
    assert SERVICE.is_market_open(saturday) is True
    assert SERVICE.get_session_start(saturday).strftime("%H:%M") == "09:50"


def test_weekend_session_boundaries():
    assert SERVICE.get_session(datetime(2026, 9, 5, 9, 49, 59, tzinfo=MSK)) == "CLOSED"
    assert SERVICE.get_session(datetime(2026, 9, 5, 9, 50, tzinfo=MSK)) == "WEEKEND_SESSION"
    assert SERVICE.get_session(datetime(2026, 9, 5, 18, 59, 59, tzinfo=MSK)) == "WEEKEND_SESSION"
    assert SERVICE.get_session(datetime(2026, 9, 5, 19, 0, tzinfo=MSK)) == "CLOSED"


def test_non_trading_weekend_is_closed():
    saturday = datetime(2026, 9, 12, 10, 0, tzinfo=MSK)
    assert SERVICE.get_session(saturday) == "CLOSED"
    assert SERVICE.is_market_open(saturday) is False


def test_calendar_update_december_weekend_is_trading():
    saturday = datetime(2026, 12, 5, 10, 0, tzinfo=MSK)
    sunday = datetime(2026, 12, 6, 10, 0, tzinfo=MSK)
    assert SERVICE.get_session(saturday) == "WEEKEND_SESSION"
    assert SERVICE.get_session(sunday) == "WEEKEND_SESSION"


def test_calendar_update_november_weekend_is_closed():
    saturday = datetime(2026, 11, 28, 10, 0, tzinfo=MSK)
    sunday = datetime(2026, 11, 29, 10, 0, tzinfo=MSK)
    assert SERVICE.get_session(saturday) == "CLOSED"
    assert SERVICE.get_session(sunday) == "CLOSED"


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
    assert SERVICE.get_session(value) == "EVENING"


if __name__ == "__main__":
    for test in (
        test_session_boundaries,
        test_weekend_additional_session_is_open,
        test_weekend_session_boundaries,
        test_non_trading_weekend_is_closed,
        test_calendar_update_december_weekend_is_trading,
        test_calendar_update_november_weekend_is_closed,
        test_session_info_contains_live_clock_fields,
        test_utc_datetime_is_converted_to_moscow,
    ):
        test()
        print("PASS", test.__name__)
    print("ALL TESTS PASSED")
