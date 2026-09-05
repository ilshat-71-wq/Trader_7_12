"""Trader_7_12 Pro — Moscow market session clock for the read-only scanner."""

from datetime import datetime, date, time
from zoneinfo import ZoneInfo


class MarketSessionService:
    """Single source of truth for the current Moscow market session.

    MOEX calendar weekends are not equivalent to ``weekday() >= 5``.
    In 2026 most weekends have an additional stock-market session (ДСВД)
    from 09:50 to 19:00 MSK. Only dates explicitly declared non-trading
    by the current MOEX calendar are closed.
    """

    TIMEZONE = ZoneInfo("Europe/Moscow")
    PRE_OPEN_START = time(6, 50)
    MORNING_START = time(7, 0)
    MAIN_START = time(10, 0)
    WEEKEND_SESSION_START = time(9, 50)
    EVENING_START = time(19, 0)
    MARKET_CLOSE = time(23, 50)

    # MOEX 2026 weekend calendar. 28–29 Nov became non-trading after the
    # September 2026 calendar update; 5–6 Dec became trading dates instead.
    NON_TRADING_WEEKEND_DATES_2026 = frozenset(
        date(2026, month, day)
        for month, day in (
            (1, 3), (1, 4), (1, 10), (1, 11),
            (2, 14), (2, 15),
            (3, 7), (3, 8), (3, 21), (3, 22),
            (5, 9), (5, 10),
            (6, 20), (6, 21),
            (8, 1), (8, 2), (8, 15), (8, 16),
            (9, 12), (9, 13),
            (10, 24), (10, 25),
            (11, 28), (11, 29),
        )
    )

    LABELS = {
        "PRE_OPEN": "ПРЕ-ОТКРЫТИЕ",
        "MORNING": "УТРЕННЯЯ СЕССИЯ",
        "MAIN": "ОСНОВНАЯ СЕССИЯ",
        "WEEKEND_SESSION": "ДОПОЛНИТЕЛЬНАЯ СЕССИЯ ВЫХОДНОГО ДНЯ",
        "EVENING": "ВЕЧЕРНЯЯ СЕССИЯ",
        "CLOSED": "РЫНОК ЗАКРЫТ",
    }
    WINDOWS = {
        "PRE_OPEN": (PRE_OPEN_START, MORNING_START),
        "MORNING": (MORNING_START, MAIN_START),
        "MAIN": (MAIN_START, EVENING_START),
        "WEEKEND_SESSION": (WEEKEND_SESSION_START, EVENING_START),
        "EVENING": (EVENING_START, MARKET_CLOSE),
    }

    @classmethod
    def is_weekend_trading_date(cls, value):
        """Return True when the date has MOEX's additional weekend session."""
        if value is None:
            return False
        current_date = value.date() if isinstance(value, datetime) else value
        return (
            current_date.weekday() >= 5
            and current_date not in cls.NON_TRADING_WEEKEND_DATES_2026
        )

    def now(self):
        return datetime.now(self.TIMEZONE)

    def to_moscow(self, value):
        if value is None or not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return value.astimezone(self.TIMEZONE)

    def get_session(self, value=None):
        value = self.now() if value is None else self.to_moscow(value)
        if value is None:
            return "CLOSED"
        current_time = value.time()

        if self.is_weekend_trading_date(value):
            if self.WEEKEND_SESSION_START <= current_time < self.EVENING_START:
                return "WEEKEND_SESSION"
            return "CLOSED"

        if value.weekday() >= 5:
            return "CLOSED"
        if self.PRE_OPEN_START <= current_time < self.MORNING_START:
            return "PRE_OPEN"
        if self.MORNING_START <= current_time < self.MAIN_START:
            return "MORNING"
        if self.MAIN_START <= current_time < self.EVENING_START:
            return "MAIN"
        if self.EVENING_START <= current_time < self.MARKET_CLOSE:
            return "EVENING"
        return "CLOSED"

    def get_session_label(self, value=None):
        return self.LABELS.get(self.get_session(value), "РЫНОК ЗАКРЫТ")

    def get_trading_day(self, value=None):
        value = self.now() if value is None else self.to_moscow(value)
        return value.date() if value is not None else None

    def get_session_start(self, value=None):
        """Return the actual start of the current market-data session."""
        session = self.get_session(value)
        if session == "WEEKEND_SESSION":
            return self.WEEKEND_SESSION_START
        if session in self.WINDOWS:
            return self.WINDOWS[session][0]
        return None

    def is_market_open(self, value=None):
        return self.get_session(value) in {"MORNING", "MAIN", "WEEKEND_SESSION", "EVENING"}

    def get_session_info(self, value=None):
        value = self.now() if value is None else self.to_moscow(value)
        session = self.get_session(value)
        session_start = self.get_session_start(value)
        return {
            "timezone": "Europe/Moscow",
            "datetime": value.isoformat() if value else None,
            "date": value.date().isoformat() if value else None,
            "time": value.strftime("%H:%M:%S") if value else None,
            "session": session,
            "label": self.LABELS.get(session, session),
            "market_open": self.is_market_open(value),
            "session_start": session_start.strftime("%H:%M") if session_start else None,
        }

    def get_window(self, value=None):
        return self.WINDOWS.get(self.get_session(value))
