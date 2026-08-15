"""
Trader_7_12 Pro

Historical Morning Replay Service.

Purpose:
- replay a completed trading morning without using future candles;
- evaluate the existing SPOT M5 setup detector at selected Moscow times;
- provide a deterministic weekend test path before live-market validation.

This service does not place orders and does not change trading rules.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from services.history_candle_service import HistoryCandleService
from services.instrument_morning_radar_service import InstrumentMorningRadarService


class MorningReplayService:
    """Replay the existing morning setup logic on a historical date."""

    VERSION = "0.1"
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    MORNING_START = time(7, 0)
    MORNING_END = time(10, 0)

    def __init__(self, history_service=None, radar_service=None):
        self.history_service = history_service or HistoryCandleService()
        self.radar_service = radar_service or InstrumentMorningRadarService()

    @classmethod
    def _as_date(cls, value):
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=cls.MOSCOW_TZ)
            return value.astimezone(cls.MOSCOW_TZ).date()
        return date.fromisoformat(str(value)[:10])

    @classmethod
    def _as_time(cls, value):
        if isinstance(value, time):
            return value
        text = str(value).strip()
        return time.fromisoformat(text[:8])

    def load_candles(self, ticker, class_code, trading_date, end_time):
        """Load only candles that existed by the replay clock time."""
        trading_date = self._as_date(trading_date)
        end_time = self._as_time(end_time)

        start_moscow = datetime.combine(
            trading_date,
            self.MORNING_START,
            tzinfo=self.MOSCOW_TZ,
        )
        end_moscow = datetime.combine(
            trading_date,
            end_time,
            tzinfo=self.MOSCOW_TZ,
        )

        if end_moscow < start_moscow:
            return []

        candles = self.history_service.load(
            ticker,
            class_code,
            start_time=start_moscow.astimezone(timezone.utc),
            end_time=end_moscow.astimezone(timezone.utc),
            timeframe_minutes=5,
        )

        result = []
        for candle in candles:
            dt = self.history_service.to_moscow(candle.get("time"))
            if dt is None:
                continue
            if self.MORNING_START <= dt.time() <= end_time:
                result.append(candle)

        result.sort(key=lambda item: str(item.get("time") or ""))
        return result

    def replay_setup(self, ticker, class_code, direction, trading_date, checkpoints=None):
        """Evaluate setup state at each requested historical checkpoint."""
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")

        if checkpoints is None:
            checkpoints = ["07:15", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00"]

        results = []
        detector = (
            self.radar_service._detect_long_setup
            if direction == "LONG"
            else self.radar_service._detect_short_setup
        )

        for checkpoint in checkpoints:
            checkpoint = self._as_time(checkpoint)
            candles = self.load_candles(
                ticker,
                class_code,
                trading_date,
                checkpoint,
            )

            if len(candles) < 4:
                setup = self.radar_service._empty_setup(direction)
            else:
                candles = candles[-self.radar_service.SETUP_LOOKBACK_CANDLES:]
                setup = detector(candles)

            results.append({
                "version": self.VERSION,
                "ticker": ticker,
                "class_code": class_code,
                "trading_date": self._as_date(trading_date).isoformat(),
                "checkpoint": checkpoint.strftime("%H:%M"),
                "direction": direction,
                "candles": len(candles),
                "setup": setup.get("setup", "NONE"),
                "setup_state": setup.get("setup_state", "WAIT"),
                "entry_trigger": float(setup.get("entry_trigger", 0) or 0),
                "previous_high": float(setup.get("previous_high", 0) or 0),
                "previous_low": float(setup.get("previous_low", 0) or 0),
            })

        return results

    @staticmethod
    def print_results(results):
        print()
        print("=" * 100)
        print("TRADER_7_12 PRO - HISTORICAL MORNING REPLAY")
        print("READ ONLY — NO ORDERS")
        print("=" * 100)
        print(f"{'TIME':<8}{'DIR':<7}{'CANDLES':<9}{'SETUP':<18}{'STATE':<8}{'TRIGGER':>12}{'HIGH':>12}{'LOW':>12}")
        print("-" * 100)
        for item in results:
            print(
                f"{item['checkpoint']:<8}"
                f"{item['direction']:<7}"
                f"{item['candles']:<9}"
                f"{item['setup']:<18}"
                f"{item['setup_state']:<8}"
                f"{item['entry_trigger']:>12.4f}"
                f"{item['previous_high']:>12.4f}"
                f"{item['previous_low']:>12.4f}"
            )
        print("=" * 100)
