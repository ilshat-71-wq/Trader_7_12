"""Trader_7_12 Pro — Moscow market session service."""

from datetime import datetime, time
from zoneinfo import ZoneInfo


class MarketSessionService:
    """Single source of truth for the application's market clock."""

    TIMEZONE = ZoneInfo("Europe/Moscow")

    PRE_OPEN_START = time(6, 50)
    MORNING_START = time(7, 0)
    MAIN_START = time(10, 0)
    EVENING_START = time(19, 0)
    MARKET_CLOSE = time(23, 50)

    LABELS = {
        "PRE_OPEN": "ПРЕ-ОТКРЫТИЕ",
        "MORNING": "УТРЕННЯЯ СЕССИЯ",
        "MAIN": "ОСНОВНАЯ СЕССИЯ",
        "EVENING": "ВЕЧЕРНЯЯ СЕССИЯ",
        "CLOSED": "РЫНОК ЗАКРЫТ",
    }

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
        if self.PRE_OPEN_START <= current_time < self.MORNING_START:
            return "PRE_OPEN"
        if self.MORNING_START <= current_time < self.MAIN_START:
            return "MORNING"
        if self.MAIN_START <= current_time < self.EVENING_START:
            return "MAIN"
        if self.EVENING_START <= current_time < self.MARKET_CLOSE:
            return "EVENING"
        return "CLOSED"

    def get_trading_day(self, value=None):
        value = self.now() if value is None else self.to_moscow(value)
        return value.date() if value else None

    def is_morning(self, value=None):
        return self.get_session(value) == "MORNING"

    def is_main(self, value=None):
        return self.get_session(value) == "MAIN"

    def is_evening(self, value=None):
        return self.get_session(value) == "EVENING"

    def is_market_open(self, value=None):
        return self.get_session(value) in {"MORNING", "MAIN", "EVENING"}

    def get_session_label(self, value=None):
        return self.LABELS.get(self.get_session(value), "РЫНОК ЗАКРЫТ")

    def get_session_info(self, value=None):
        value = self.now() if value is None else self.to_moscow(value)
        session = self.get_session(value)
        return {
            "timezone": "Europe/Moscow",
            "datetime": value.isoformat() if value else None,
            "date": value.date().isoformat() if value else None,
            "time": value.strftime("%H:%M:%S") if value else None,
            "session": session,
            "label": self.LABELS.get(session, session),
            "market_open": session in {"MORNING", "MAIN", "EVENING"},
        }
