"""
Trader_7_12 Pro

Market Session Service
Версия 0.1

Все торговые времена проекта:
Europe/Moscow (UTC+3).

Срочный рынок MOEX:

06:50–07:00  PRE_OPEN
07:00–10:00  MORNING
10:00–19:00  MAIN
19:00–23:50  EVENING
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo


class MarketSessionService:

    TIMEZONE = ZoneInfo("Europe/Moscow")

    PRE_OPEN_START = time(6, 50)
    MORNING_START = time(7, 0)
    MAIN_START = time(10, 0)
    EVENING_START = time(19, 0)
    MARKET_CLOSE = time(23, 50)

    # ---------------------------------------------------------
    # NOW
    # ---------------------------------------------------------

    def now(self):

        return datetime.now(
            self.TIMEZONE
        )

    # ---------------------------------------------------------
    # UTC -> MOSCOW
    # ---------------------------------------------------------

    def to_moscow(self, value):

        if value is None:
            return None

        if not isinstance(value, datetime):
            return None

        if value.tzinfo is None:

            value = value.replace(
                tzinfo=ZoneInfo("UTC")
            )

        return value.astimezone(
            self.TIMEZONE
        )

    # ---------------------------------------------------------
    # SESSION
    # ---------------------------------------------------------

    def get_session(self, value=None):

        if value is None:

            value = self.now()

        else:

            value = self.to_moscow(
                value
            )

        if value is None:
            return "CLOSED"

        current_time = value.time()

        if (
            self.PRE_OPEN_START
            <= current_time
            < self.MORNING_START
        ):

            return "PRE_OPEN"

        if (
            self.MORNING_START
            <= current_time
            < self.MAIN_START
        ):

            return "MORNING"

        if (
            self.MAIN_START
            <= current_time
            < self.EVENING_START
        ):

            return "MAIN"

        if (
            self.EVENING_START
            <= current_time
            < self.MARKET_CLOSE
        ):

            return "EVENING"

        return "CLOSED"

    # ---------------------------------------------------------
    # TRADING DAY
    # ---------------------------------------------------------

    def get_trading_day(self, value=None):

        if value is None:

            value = self.now()

        else:

            value = self.to_moscow(
                value
            )

        if value is None:
            return None

        return value.date()

    # ---------------------------------------------------------
    # MORNING
    # ---------------------------------------------------------

    def is_morning(self, value=None):

        return (
            self.get_session(value)
            == "MORNING"
        )

    # ---------------------------------------------------------
    # MAIN
    # ---------------------------------------------------------

    def is_main(self, value=None):

        return (
            self.get_session(value)
            == "MAIN"
        )

    # ---------------------------------------------------------
    # EVENING
    # ---------------------------------------------------------

    def is_evening(self, value=None):

        return (
            self.get_session(value)
            == "EVENING"
        )

    # ---------------------------------------------------------
    # MARKET OPEN
    # ---------------------------------------------------------

    def is_market_open(self, value=None):

        return (
            self.get_session(value)
            in {
                "MORNING",
                "MAIN",
                "EVENING"
            }
        )

    # ---------------------------------------------------------
    # SESSION INFO
    # ---------------------------------------------------------

    def get_session_info(self, value=None):

        if value is None:

            value = self.now()

        else:

            value = self.to_moscow(
                value
            )

        session = self.get_session(
            value
        )

        return {
            "timezone": "Europe/Moscow",

            "datetime": (
                value.isoformat()
                if value
                else None
            ),

            "date": (
                value.date().isoformat()
                if value
                else None
            ),

            "session": session,

            "market_open": (
                session
                in {
                    "MORNING",
                    "MAIN",
                    "EVENING"
                }
            )
        }
