"""
Trader_7_12 Pro

Historical Morning Replay Service.

Purpose:
- replay a completed trading morning without using future candles;
- evaluate the canonical SPOT first-pullback/rebound detector at selected Moscow times;
- calculate SPOT momentum at each checkpoint using only candles already available;
- provide a deterministic weekend test path before live-market validation.

This service does not place orders and does not change trading rules.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from services.history_candle_service import HistoryCandleService
from services.instrument_morning_radar_service import InstrumentMorningRadarService
from services.momentum_service import MomentumService
from services.spot_first_pullback_service import SpotFirstPullbackService


class _ReplaySessionAdapter:
    """Minimal session adapter for the canonical SPOT setup detector."""

    def __init__(self, trading_date):
        self.trading_date = trading_date

    def get_session(self):
        return "MORNING"

    def get_trading_day(self):
        return self.trading_date


class MorningReplayService:
    """Replay canonical SPOT setup logic on a historical date."""

    VERSION = "0.4"
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    MORNING_START = time(7, 0)
    MORNING_END = time(10, 0)
    MOMENTUM_AVERAGE_CANDLES = 5

    def __init__(self, history_service=None, radar_service=None, setup_engine=None, momentum_service=None):
        self.history_service = history_service or HistoryCandleService()
        self.radar_service = radar_service or InstrumentMorningRadarService()
        # setup_engine is retained as a compatibility parameter only. Historical
        # replay now uses SpotFirstPullbackService as the canonical setup engine.
        self.setup_engine = None
        self.momentum_service = momentum_service or MomentumService()
        self._spot_setup_cache = {}

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

    def _spot_setup_service(self, trading_date):
        trading_date = self._as_date(trading_date)
        key = trading_date.isoformat()
        service = self._spot_setup_cache.get(key)
        if service is None:
            service = SpotFirstPullbackService(
                history_service=self.history_service,
                session_service=_ReplaySessionAdapter(trading_date),
            )
            self._spot_setup_cache[key] = service
        return service

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

    def calculate_momentum(self, candles):
        """Calculate momentum from the latest available candle only."""
        if not candles:
            return self.momentum_service.analyze({})

        current = candles[-1]
        history = candles[:-1]
        baseline = history[-self.MOMENTUM_AVERAGE_CANDLES:]

        volumes = []
        money_volumes = []
        for item in baseline:
            try:
                close = float(item.get("close") or 0)
                volume = float(item.get("volume") or 0)
            except (TypeError, ValueError):
                continue
            if close > 0 and volume > 0:
                volumes.append(volume)
                money_volumes.append(close * volume)

        average_volume = sum(volumes) / len(volumes) if volumes else 0.0
        average_money_volume = sum(money_volumes) / len(money_volumes) if money_volumes else 0.0

        previous = history[-1] if history else {}
        try:
            previous_high = float(previous.get("high") or 0)
            previous_low = float(previous.get("low") or 0)
        except (TypeError, ValueError):
            previous_high = 0.0
            previous_low = 0.0

        return self.momentum_service.analyze(
            current,
            average_volume=average_volume,
            average_money_volume=average_money_volume,
            previous_high=previous_high,
            previous_low=previous_low,
        )

    def replay_setup(self, ticker, class_code, direction, trading_date, checkpoints=None):
        """Evaluate canonical SPOT setup and momentum at each historical checkpoint.

        The setup detector receives only candles available at the checkpoint. We
        deliberately do not call SpotFirstPullbackService.analyze(), because its
        live-session loader would see candles after the replay clock time.
        """
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")

        if checkpoints is None:
            checkpoints = ["07:15", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00"]

        setup_service = self._spot_setup_service(trading_date)
        results = []

        for checkpoint in checkpoints:
            checkpoint = self._as_time(checkpoint)
            candles = self.load_candles(
                ticker,
                class_code,
                trading_date,
                checkpoint,
            )

            momentum = self.calculate_momentum(candles)
            setup = (
                setup_service._detect_long(candles)
                if direction == "LONG"
                else setup_service._detect_short(candles)
            )

            results.append({
                "version": self.VERSION,
                "ticker": ticker,
                "class_code": class_code,
                "trading_date": self._as_date(trading_date).isoformat(),
                "checkpoint": checkpoint.strftime("%H:%M"),
                "direction": direction,
                "candles": len(candles),
                "momentum_score": momentum.get("momentum_score", 0),
                "momentum_signal": momentum.get("signal", "NO_SIGNAL"),
                "volume_ratio": momentum.get("volume_ratio", 0),
                "money_volume_ratio": momentum.get("money_volume_ratio", 0),
                "breakout_strength": momentum.get("breakout_strength", 0),
                "setup": setup.get("setup", "NONE"),
                "setup_state": setup.get("setup_state", "WAIT"),
                "setup_phase": setup.get("setup_phase", "NO_SETUP"),
                "setup_quality_score": float(setup.get("setup_quality_score", 0) or 0),
                "retracement_percent": float(setup.get("retracement_percent", 0) or 0),
                "retracement_ratio": float(setup.get("retracement_ratio", 0) or 0),
                "entry_trigger": float(setup.get("entry_trigger", 0) or 0),
                "previous_high": float(setup.get("previous_high", 0) or 0),
                "previous_low": float(setup.get("previous_low", 0) or 0),
                "setup_index": None,
                "confirmation_index": None,
            })

        return results

    @staticmethod
    def print_results(results):
        print()
        print("=" * 140)
        print("TRADER_7_12 PRO - HISTORICAL MORNING REPLAY")
        print("READ ONLY — NO ORDERS")
        print("=" * 140)
        print(
            f"{'TIME':<8}{'DIR':<7}{'MOM':>7}{'MOMENTUM':<15}"
            f"{'VOL R':>8}{'MONEY R':>9}{'SETUP':<18}"
            f"{'STATE':<10}{'TRIGGER':>12}{'QUALITY':>9}"
        )
        print("-" * 140)
        for item in results:
            print(
                f"{item['checkpoint']:<8}"
                f"{item['direction']:<7}"
                f"{item['momentum_score']:>7}"
                f"{item['momentum_signal']:<15}"
                f"{item['volume_ratio']:>8.2f}"
                f"{item['money_volume_ratio']:>9.2f}"
                f"{item['setup']:<18}"
                f"{item['setup_state']:<10}"
                f"{item['entry_trigger']:>12.4f}"
                f"{item['setup_quality_score']:>9.1f}"
            )
        print("=" * 140)
