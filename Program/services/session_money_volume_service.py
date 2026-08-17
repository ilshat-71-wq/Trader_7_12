"""Trader_7_12 Pro — current-session SPOT money/activity service."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from services.market_session_service import MarketSessionService


class SessionMoneyVolumeService:
    """Calculate current-day SPOT money volume for the active MOEX session."""

    VERSION = "0.1"
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    SESSION_WINDOWS = {
        "MORNING": (time(7, 0), time(10, 0)),
        "MAIN": (time(10, 0), time(19, 0)),
        "EVENING": (time(19, 0), time(23, 50)),
    }

    def __init__(self, history_service=None, session_service=None):
        if history_service is None:
            from services.history_candle_service import HistoryCandleService
            history_service = HistoryCandleService()
        self.history_service = history_service
        self.session_service = session_service or MarketSessionService()

    def _utc_window(self, trading_date, start_time, end_time):
        start = datetime.combine(trading_date, start_time, tzinfo=self.MOSCOW_TZ)
        end = datetime.combine(trading_date, end_time, tzinfo=self.MOSCOW_TZ)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    def calculate(self, ticker, class_code, trading_date=None, timeframe_minutes=5, session=None):
        """Return current-session money and normalized activity metrics."""
        now = self.session_service.now()
        if trading_date is None:
            trading_date = now.date()

        session = str(session or self.session_service.get_session()).upper()
        window = self.SESSION_WINDOWS.get(session)
        if window is None:
            return {
                "session": session,
                "money_volume": 0.0,
                "elapsed_minutes": 0,
                "expected_minutes": 0,
                "money_per_minute": 0.0,
            }

        start_time, end_time = window
        effective_end = min(now.time(), end_time)
        if trading_date != now.date():
            effective_end = end_time

        if effective_end <= start_time:
            return {
                "session": session,
                "money_volume": 0.0,
                "elapsed_minutes": 0,
                "expected_minutes": int((datetime.combine(trading_date, end_time) - datetime.combine(trading_date, start_time)).total_seconds() / 60),
                "money_per_minute": 0.0,
            }

        start_utc, _ = self._utc_window(trading_date, start_time, end_time)
        end = datetime.combine(trading_date, effective_end, tzinfo=self.MOSCOW_TZ).astimezone(timezone.utc)

        candles = self.history_service.load(
            ticker,
            class_code,
            start_time=start_utc,
            end_time=end,
            timeframe_minutes=timeframe_minutes,
        )

        total = 0.0
        for candle in candles:
            try:
                money = float(candle.get("money_volume", 0) or 0)
            except (TypeError, ValueError):
                continue
            if money > 0:
                total += money

        elapsed_minutes = max(
            0,
            int((datetime.combine(trading_date, effective_end) - datetime.combine(trading_date, start_time)).total_seconds() / 60),
        )
        expected_minutes = int(
            (datetime.combine(trading_date, end_time) - datetime.combine(trading_date, start_time)).total_seconds() / 60
        )

        return {
            "session": session,
            "money_volume": round(total, 2),
            "elapsed_minutes": elapsed_minutes,
            "expected_minutes": expected_minutes,
            "money_per_minute": round(total / elapsed_minutes, 2) if elapsed_minutes else 0.0,
        }
