"""MOEX-style price-instability detector for the SPOT-first scanner.

The scanner does not consume MOEX ISS data for trading decisions. Instead it
uses authenticated BCS candles and applies the published MOEX price-instability
rules to those broker market-data candles.

IMOEX equities:
- discrete-auction threshold: +/-20% for 10 minutes;
- weekend DSVT: fixed +/-3% band, with no discrete auction.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


class MoexPriceStabilityService:
    VERSION = "0.1"
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    DA_TRIGGER_PERCENT = 20.0
    DA_WINDOW_MINUTES = 10
    WEEKEND_BAND_PERCENT = 3.0
    WEEKEND_NEAR_PERCENT = 2.5
    LOOKBACK_CALENDAR_DAYS = 4
    CANDLE_TIMEFRAME = "M5"
    WEEKEND_START = time(9, 50)
    WEEKEND_END = time(19, 0)

    def __init__(self, api):
        self.api = api

    @classmethod
    def _to_moscow(cls, value):
        if value is None:
            return None
        try:
            text = str(value).strip()
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=cls.MOSCOW_TZ)
            return dt.astimezone(cls.MOSCOW_TZ)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _valid_bar(cls, bar):
        if not isinstance(bar, dict):
            return False
        try:
            close = float(bar.get("close", 0) or 0)
            high = float(bar.get("high", 0) or 0)
            low = float(bar.get("low", 0) or 0)
        except (TypeError, ValueError):
            return False
        return close > 0 and high > 0 and low > 0 and high >= low

    @classmethod
    def _is_weekend_session(cls, dt):
        if dt is None or dt.weekday() not in {5, 6}:
            return False
        return cls.WEEKEND_START <= dt.time() < cls.WEEKEND_END

    @classmethod
    def _bar_excursion(cls, bar, reference_close):
        if reference_close <= 0 or not cls._valid_bar(bar):
            return 0.0
        high = float(bar.get("high") or 0)
        low = float(bar.get("low") or 0)
        return max(
            abs((high - reference_close) / reference_close * 100.0),
            abs((low - reference_close) / reference_close * 100.0),
        )

    @classmethod
    def _consecutive_da_trigger(cls, bars, reference_close):
        if reference_close <= 0:
            return False

        eligible = []
        for bar in bars:
            dt = cls._to_moscow(bar.get("time"))
            if dt is None or cls._is_weekend_session(dt):
                continue
            if not cls._valid_bar(bar):
                continue
            eligible.append((dt, cls._bar_excursion(bar, reference_close)))

        eligible.sort(key=lambda item: item[0])
        for index in range(1, len(eligible)):
            previous_dt, previous_excursion = eligible[index - 1]
            current_dt, current_excursion = eligible[index]
            if (current_dt - previous_dt) > timedelta(minutes=5):
                continue
            if (
                previous_excursion >= cls.DA_TRIGGER_PERCENT
                and current_excursion >= cls.DA_TRIGGER_PERCENT
            ):
                return True
        return False

    def evaluate(self, ticker, class_code, reference_close, trading_date=None, now=None):
        try:
            reference_close = float(reference_close or 0)
        except (TypeError, ValueError):
            reference_close = 0.0

        result = {
            "version": self.VERSION,
            "moex_event_risk": False,
            "moex_da_trigger_inferred": False,
            "moex_da_trigger_percent": self.DA_TRIGGER_PERCENT,
            "moex_da_window_minutes": self.DA_WINDOW_MINUTES,
            "moex_weekend_band_percent": self.WEEKEND_BAND_PERCENT,
            "moex_weekend_band_near": False,
            "moex_weekend_band_hit": False,
            "moex_max_abs_move_percent": 0.0,
            "moex_price_stability_state": "NORMAL",
            "moex_price_stability_reason": "",
            "moex_candles_loaded": 0,
            "moex_data_status": "NO_DATA",
        }

        if reference_close <= 0:
            result["moex_data_status"] = "NO_REFERENCE_CLOSE"
            return result

        if now is None:
            now = datetime.now(self.MOSCOW_TZ)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=self.MOSCOW_TZ)
        else:
            now = now.astimezone(self.MOSCOW_TZ)

        start = now - timedelta(days=self.LOOKBACK_CALENDAR_DAYS)
        try:
            payload = self.api.get_candles(
                ticker,
                class_code,
                interval=self.CANDLE_TIMEFRAME,
                start_time=start,
                end_time=now,
            )
        except Exception as exc:
            result["moex_data_status"] = "ERROR"
            result["moex_price_stability_reason"] = type(exc).__name__
            return result

        bars = payload.get("bars", []) if isinstance(payload, dict) else []
        if not isinstance(bars, list):
            bars = []
        bars = [bar for bar in bars if self._valid_bar(bar)]
        bars.sort(key=lambda bar: self._to_moscow(bar.get("time")) or now)

        # Normal working-day scan: use only the current trading date.
        # Monday additionally includes the weekend DSVT because MOEX treats
        # Saturday/Sunday DSVT as part of the next ordinary trading day.
        target_date = trading_date
        if hasattr(target_date, "isoformat"):
            target_date = target_date
        else:
            try:
                target_date = datetime.fromisoformat(str(target_date)[:10]).date()
            except (TypeError, ValueError):
                target_date = now.date()

        relevant = []
        for bar in bars:
            dt = self._to_moscow(bar.get("time"))
            if dt is None:
                continue
            if dt.date() == target_date:
                relevant.append(bar)
                continue
            if target_date.weekday() == 0 and self._is_weekend_session(dt):
                relevant.append(bar)

        result["moex_candles_loaded"] = len(relevant)
        result["moex_data_status"] = "OK" if relevant else "NO_DATA"
        if not relevant:
            return result

        max_excursion = max(
            self._bar_excursion(bar, reference_close)
            for bar in relevant
        )
        result["moex_max_abs_move_percent"] = round(max_excursion, 2)

        weekend_bars = [
            bar for bar in relevant
            if self._is_weekend_session(self._to_moscow(bar.get("time")))
        ]
        weekend_max = max(
            [self._bar_excursion(bar, reference_close) for bar in weekend_bars]
            or [0.0]
        )

        if weekend_max >= self.WEEKEND_BAND_PERCENT:
            result["moex_weekend_band_hit"] = True
        elif weekend_max >= self.WEEKEND_NEAR_PERCENT:
            result["moex_weekend_band_near"] = True

        da_triggered = self._consecutive_da_trigger(relevant, reference_close)
        result["moex_da_trigger_inferred"] = da_triggered

        if da_triggered:
            result["moex_event_risk"] = True
            result["moex_price_stability_state"] = "EVENT_DRIVEN"
            result["moex_price_stability_reason"] = "MOEX_DA_TRIGGER_INFERRED"
        elif max_excursion >= self.DA_TRIGGER_PERCENT:
            result["moex_event_risk"] = True
            result["moex_price_stability_state"] = "EVENT_DRIVEN"
            result["moex_price_stability_reason"] = "MOEX_DA_THRESHOLD_REACHED"
        elif result["moex_weekend_band_hit"]:
            result["moex_event_risk"] = True
            result["moex_price_stability_state"] = "WEEKEND_BAND_EVENT"
            result["moex_price_stability_reason"] = "WEEKEND_BAND_HIT"
        elif result["moex_weekend_band_near"]:
            result["moex_event_risk"] = True
            result["moex_price_stability_state"] = "WEEKEND_BAND_NEAR"
            result["moex_price_stability_reason"] = "WEEKEND_BAND_NEAR"

        return result
