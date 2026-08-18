"""
Trader_7_12 Pro

Instrument Morning Radar Service
Версия 0.4

Назначение:

- единый spot-first Morning Radar для выбранных ликвидных акций;
- дневной тренд по завершённым D-свечам;
- средний дневной денежный оборот;
- Relative Strength относительно IMOEX2/IRUS2;
- единый предварительный radar score;
- определение первого утреннего setup;
- подготовка результата для следующего этапа scanner.

Архитектурные правила:

1. Главный benchmark: IMOEX2 / IRUS2, class code определяется динамически через BCS.
2. RS не смешивается с Radar Score на этом этапе.
3. Текущий незавершённый торговый день не участвует
   в дневном тренде и Relative Strength.
4. Для D-свечей BCS торговая дата определяется по UTC.
5. M5 money volume не используется в торговом рейтинге.
6. Radar не открывает сделки.
7. Setup определяется по SPOT M5.
8. setup_state=READY возникает только после фактического
   подтверждения уровня последующей свечой.
"""

from datetime import datetime, timezone

from services.morning_radar_service import MorningRadarService
from services.history_candle_service import HistoryCandleService
from services.relative_strength_service import RelativeStrengthService


class InstrumentMorningRadarService:

    VERSION = "0.4"

    BENCHMARK_TICKERS = ("IMOEX2", "IRUS2")

    MORNING_TIMEFRAME_MINUTES = 5
    MIN_IMPULSE_CANDLES = 2
    MIN_IMPULSE_MOVE_PERCENT = 0.15
    MAX_PULLBACK_PERCENT = 0.80
    SETUP_LOOKBACK_CANDLES = 36

    def __init__(self):
        self.radar_service = MorningRadarService()
        self.history_service = HistoryCandleService()
        self.relative_strength_service = RelativeStrengthService()
        self._benchmark_candles = None

    # ---------------------------------------------------------
    # BENCHMARK
    # ---------------------------------------------------------

    def load_benchmark_candles(self):
        if self._benchmark_candles is not None:
            return self._benchmark_candles

        api = self.history_service.trade_service.api
        records = []

        try:
            records = api.get_instruments("INDICES")
        except Exception:
            records = []

        def resolve(items):
            for ticker in self.BENCHMARK_TICKERS:
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    item_ticker = str(
                        item.get("ticker") or ""
                    ).strip().upper()

                    if item_ticker != ticker:
                        continue

                    class_code = str(
                        item.get("classCode") or ""
                    ).strip()

                    if not class_code:
                        for board in item.get("boards") or []:
                            if not isinstance(board, dict):
                                continue
                            class_code = str(
                                board.get("classCode") or ""
                            ).strip()
                            if class_code:
                                break

                    if class_code:
                        return ticker, class_code

            return None

        resolved = resolve(records)

        if resolved is None:
            lookup = getattr(
                api,
                "get_instruments_by_tickers",
                None
            )

            if callable(lookup):
                try:
                    records = lookup(
                        list(self.BENCHMARK_TICKERS)
                    )
                except Exception:
                    records = []

                if isinstance(records, list):
                    resolved = resolve(records)

        if resolved is None:
            print(
                "❌ IMOEX2/IRUS2 benchmark unavailable"
            )
            self._benchmark_candles = []
            return self._benchmark_candles

        ticker, class_code = resolved

        try:
            candles = self.history_service.load_daily(
                ticker,
                class_code
            )
        except Exception as exc:
            print(
                "❌ benchmark error:",
                ticker,
                class_code,
                exc
            )
            candles = []

        if not isinstance(candles, list):
            candles = []

        self._benchmark_candles = candles
        self._benchmark_name = f"{ticker}/{class_code}"

        return candles

    # ---------------------------------------------------------
    # UTC TRADING DATE
    # ---------------------------------------------------------

    @staticmethod
    def _utc_trading_date(value):
        """Return the trading date encoded by a BCS D-candle timestamp."""
        if value is None:
            return None

        try:
            if isinstance(value, datetime):
                dt = value
            else:
                text = str(value).strip()

                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"

                dt = datetime.fromisoformat(text)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).date()

        except (TypeError, ValueError):
            return None

    def _build_close_map(self, candles):
        result = {}

        if not isinstance(candles, list):
            return result

        for candle in candles:
            if not isinstance(candle, dict):
                continue

            day = self._utc_trading_date(candle.get("time"))

            if day is None:
                continue

            try:
                close = float(candle.get("close", 0) or 0)
            except (TypeError, ValueError):
                continue

            if close <= 0:
                continue

            result[day] = close

        return result

    # ---------------------------------------------------------
    # RELATIVE STRENGTH
    # ---------------------------------------------------------

    def calculate_relative_strength_from_candles(
        self,
        instrument_candles,
        benchmark_candles=None
    ):
        """Calculate RS using the two latest common daily dates."""

        if benchmark_candles is None:
            benchmark_candles = self.load_benchmark_candles()

        instrument_map = self._build_close_map(
            instrument_candles
        )

        benchmark_map = self._build_close_map(
            benchmark_candles
        )

        common_dates = sorted(
            set(instrument_map) & set(benchmark_map)
        )

        benchmark_name = (
            getattr(self, "_benchmark_name", "IMOEX2/IRUS2")
        )

        if len(common_dates) < 2:
            return {
                "status": "NO_DATA",
                "error": (
                    "Not enough common daily candles with IMOEX2/IRUS2"
                ),
                "relative_strength": 0.0,
                "relative_strength_score": 50.0,
                "relative_strength_signal": "NEUTRAL",
                "previous_date": None,
                "current_date": None,
                "benchmark": benchmark_name,
            }

        previous_date = common_dates[-2]
        current_date = common_dates[-1]

        result = self.relative_strength_service.calculate(
            instrument_previous=instrument_map[previous_date],
            instrument_current=instrument_map[current_date],
            benchmark_previous=benchmark_map[previous_date],
            benchmark_current=benchmark_map[current_date],
        )

        if not isinstance(result, dict):
            result = {
                "relative_strength": 0.0,
                "relative_strength_score": 50.0,
                "relative_strength_signal": "NEUTRAL",
            }

        result["status"] = "OK"
        result["previous_date"] = previous_date.isoformat()
        result["current_date"] = current_date.isoformat()
        result["benchmark"] = benchmark_name

        return result

    def calculate_relative_strength(
        self,
        ticker,
        class_code
    ):
        try:
            instrument_candles = self.history_service.load_daily(
                ticker,
                class_code
            )
        except Exception as exc:
            return {
                "status": "ERROR",
                "error": str(exc),
                "relative_strength": 0.0,
                "relative_strength_score": 50.0,
                "relative_strength_signal": "NEUTRAL",
            }

        return self.calculate_relative_strength_from_candles(
            instrument_candles,
            self.load_benchmark_candles()
        )

    # ---------------------------------------------------------
    # TREND SCORE
    # ---------------------------------------------------------

    @staticmethod
    def calculate_trend_score(trend):
        if not isinstance(trend, dict):
            return 0

        direction = str(
            trend.get("direction", "")
        ).upper()

        state = str(
            trend.get("state", "")
        ).upper()

        try:
            days = int(
                trend.get("days", 0) or 0
            )
        except (TypeError, ValueError):
            days = 0

        try:
            change_percent = float(
                trend.get("change_percent", 0) or 0
            )
        except (TypeError, ValueError):
            change_percent = 0.0

        score = (
            20
            if direction in {"LONG", "SHORT"}
            else 0
        )

        if state in {
            "STRONG_UPTREND",
            "STRONG_DOWNTREND",
        }:
            score += 35

        elif state in {
            "UPTREND",
            "DOWNTREND",
        }:
            score += 25

        elif state in {
            "WEAK_UPTREND",
            "WEAK_DOWNTREND",
        }:
            score += 10

        if days >= 5:
            score += 25

        elif days >= 4:
            score += 20

        elif days >= 3:
            score += 15

        elif days >= 2:
            score += 5

        abs_change = abs(change_percent)

        if abs_change >= 5:
            score += 20

        elif abs_change >= 3:
            score += 15

        elif abs_change >= 1:
            score += 5

        return min(score, 100)

    # ---------------------------------------------------------
    # MONEY SCORE
    # ---------------------------------------------------------

    @staticmethod
    def calculate_money_score(money):
        if not isinstance(money, dict):
            return 0

        try:
            average_money = float(
                money.get(
                    "average_daily_money_volume",
                    0
                ) or 0
            )
        except (TypeError, ValueError):
            return 0

        if average_money >= 1_000_000_000:
            return 50

        if average_money >= 500_000_000:
            return 45

        if average_money >= 100_000_000:
            return 35

        if average_money >= 50_000_000:
            return 25

        if average_money >= 10_000_000:
            return 15

        if average_money >= 1_000_000:
            return 5

        return 0

    @staticmethod
    def calculate_radar_score(
        trend_score,
        money_score
    ):
        raw_score = (
            float(trend_score)
            + float(money_score)
        )

        return round(
            min(raw_score / 150 * 100, 100),
            2
        )

    @staticmethod
    def _preliminary_signal(
        radar_score,
        direction
    ):
        if radar_score >= 70:

            if direction == "LONG":
                return "LONG_WATCH"

            if direction == "SHORT":
                return "SHORT_WATCH"

            return "WATCH"

        if radar_score >= 50:
            return "WATCH"

        return "SKIP"

    # ---------------------------------------------------------
    # MORNING SETUP HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _valid_candle(cls, candle):
        if not isinstance(candle, dict):
            return False

        close = cls._safe_float(
            candle.get("close")
        )

        high = cls._safe_float(
            candle.get("high")
        )

        low = cls._safe_float(
            candle.get("low")
        )

        return (
            close > 0
            and high > 0
            and low > 0
            and high >= low
        )

    @staticmethod
    def _candle_sort_key(value):
        if value is None:
            return ""

        try:
            text = str(value).strip()

            if text.endswith("Z"):
                text = text[:-1] + "+00:00"

            return datetime.fromisoformat(text).astimezone(
                timezone.utc
            )

        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)

    @classmethod
    def _empty_setup(cls, direction="NONE"):
        return {
            "setup": "NONE",
            "setup_direction": direction,
            "setup_state": "WAIT",
            "entry_trigger": 0.0,
            "previous_high": 0.0,
            "previous_low": 0.0,
        }

    # ---------------------------------------------------------
    # LONG SETUP
    # ---------------------------------------------------------

    @classmethod
    def _detect_long_setup(cls, candles):
        """
        Detect:

            upward impulse
                ->
            first pullback
                ->
            break of pullback high

        READY is returned only when a later candle closes above
        the pullback high.
        """

        impulse_start = None
        impulse_high = 0.0
        impulse_low = 0.0

        pullback_high = 0.0
        pullback_low = 0.0
        pullback_started = False

        for index in range(
            1,
            len(candles)
        ):
            previous = candles[index - 1]
            current = candles[index]

            previous_close = cls._safe_float(
                previous.get("close")
            )

            current_close = cls._safe_float(
                current.get("close")
            )

            if (
                previous_close <= 0
                or current_close <= 0
            ):
                continue

            change_percent = (
                (
                    current_close
                    - previous_close
                )
                / previous_close
                * 100.0
            )

            if not pullback_started:

                if change_percent >= cls.MIN_IMPULSE_MOVE_PERCENT:

                    if impulse_start is None:
                        impulse_start = index - 1
                        impulse_low = cls._safe_float(
                            previous.get("low")
                        )

                    impulse_high = max(
                        impulse_high,
                        cls._safe_float(
                            current.get("high")
                        )
                    )

                    continue

                if (
                    impulse_start is not None
                    and current_close < impulse_high
                ):
                    pullback_started = True

                    pullback_high = cls._safe_float(
                        previous.get("high")
                    )

                    pullback_low = cls._safe_float(
                        current.get("low")
                    )

                    continue

            else:

                pullback_high = max(
                    pullback_high,
                    cls._safe_float(
                        current.get("high")
                    )
                )

                pullback_low = min(
                    pullback_low,
                    cls._safe_float(
                        current.get("low")
                    )
                )

                if impulse_high <= 0:
                    continue

                pullback_depth = (
                    (
                        impulse_high
                        - pullback_low
                    )
                    / impulse_high
                    * 100.0
                )

                if (
                    pullback_depth
                    > cls.MAX_PULLBACK_PERCENT
                ):
                    return {
                        "setup": "FIRST_PULLBACK",
                        "setup_direction": "LONG",
                        "setup_state": "WAIT",
                        "entry_trigger": 0.0,
                        "previous_high": round(
                            pullback_high,
                            8
                        ),
                        "previous_low": round(
                            pullback_low,
                            8
                        ),
                    }

                if current_close > pullback_high:

                    return {
                        "setup": "FIRST_PULLBACK",
                        "setup_direction": "LONG",
                        "setup_state": "READY",
                        "entry_trigger": round(
                            pullback_high,
                            8
                        ),
                        "previous_high": round(
                            pullback_high,
                            8
                        ),
                        "previous_low": round(
                            pullback_low,
                            8
                        ),
                    }

        if impulse_start is None:
            return cls._empty_setup("LONG")

        return {
            "setup": (
                "FIRST_PULLBACK"
                if pullback_started
                else "NONE"
            ),
            "setup_direction": "LONG",
            "setup_state": "WAIT",
            "entry_trigger": 0.0,
            "previous_high": round(
                pullback_high
                or impulse_high,
                8
            ),
            "previous_low": round(
                pullback_low
                or impulse_low,
                8
            ),
        }

    # ---------------------------------------------------------
    # SHORT SETUP
    # ---------------------------------------------------------

    @classmethod
    def _detect_short_setup(cls, candles):
        """
        Detect:

            downward impulse
                ->
            first rebound
                ->
            break of rebound low

        READY is returned only when a later candle closes below
        the rebound low.
        """

        impulse_start = None
        impulse_low = 0.0
        impulse_high = 0.0

        rebound_high = 0.0
        rebound_low = 0.0
        rebound_started = False

        for index in range(
            1,
            len(candles)
        ):
            previous = candles[index - 1]
            current = candles[index]

            previous_close = cls._safe_float(
                previous.get("close")
            )

            current_close = cls._safe_float(
                current.get("close")
            )

            if (
                previous_close <= 0
                or current_close <= 0
            ):
                continue

            change_percent = (
                (
                    current_close
                    - previous_close
                )
                / previous_close
                * 100.0
            )

            if not rebound_started:

                if change_percent <= (
                    -cls.MIN_IMPULSE_MOVE_PERCENT
                ):

                    if impulse_start is None:
                        impulse_start = index - 1
                        impulse_high = cls._safe_float(
                            previous.get("high")
                        )

                    impulse_low = min(
                        impulse_low
                        or cls._safe_float(
                            current.get("low")
                        ),
                        cls._safe_float(
                            current.get("low")
                        )
                    )

                    continue

                if (
                    impulse_start is not None
                    and current_close > impulse_low
                ):
                    rebound_started = True

                    rebound_high = cls._safe_float(
                        current.get("high")
                    )

                    rebound_low = cls._safe_float(
                        previous.get("low")
                    )

                    continue

            else:

                rebound_high = max(
                    rebound_high,
                    cls._safe_float(
                        current.get("high")
                    )
                )

                rebound_low = min(
                    rebound_low,
                    cls._safe_float(
                        current.get("low")
                    )
                )

                if impulse_low <= 0:
                    continue

                rebound_depth = (
                    (
                        rebound_high
                        - impulse_low
                    )
                    / impulse_low
                    * 100.0
                )

                if (
                    rebound_depth
                    > cls.MAX_PULLBACK_PERCENT
                ):
                    return {
                        "setup": "FIRST_REBOUND",
                        "setup_direction": "SHORT",
                        "setup_state": "WAIT",
                        "entry_trigger": 0.0,
                        "previous_high": round(
                            rebound_high,
                            8
                        ),
                        "previous_low": round(
                            rebound_low,
                            8
                        ),
                    }

                if current_close < rebound_low:

                    return {
                        "setup": "FIRST_REBOUND",
                        "setup_direction": "SHORT",
                        "setup_state": "READY",
                        "entry_trigger": round(
                            rebound_low,
                            8
                        ),
                        "previous_high": round(
                            rebound_high,
                            8
                        ),
                        "previous_low": round(
                            rebound_low,
                            8
                        ),
                    }

        if impulse_start is None:
            return cls._empty_setup("SHORT")

        return {
            "setup": (
                "FIRST_REBOUND"
                if rebound_started
                else "NONE"
            ),
            "setup_direction": "SHORT",
            "setup_state": "WAIT",
            "entry_trigger": 0.0,
            "previous_high": round(
                rebound_high
                or impulse_high,
                8
            ),
            "previous_low": round(
                rebound_low
                or impulse_low,
                8
            ),
        }

    # ---------------------------------------------------------
    # MORNING SETUP
    # ---------------------------------------------------------

    def calculate_morning_setup(
        self,
        ticker,
        class_code,
        direction
    ):
        """
        Calculate first morning SPOT setup using M5 candles.

        LONG:
            FIRST_PULLBACK

        SHORT:
            FIRST_REBOUND

        The setup is READY only after a later candle closes
        through the confirmation level.
        """

        direction = str(
            direction or ""
        ).upper()

        if direction not in {
            "LONG",
            "SHORT",
        }:
            return self._empty_setup(direction)

        try:
            candles = (
                self.history_service.load_morning_candles(
                    ticker,
                    class_code,
                    trading_date=(
                        self.history_service.now().date()
                    ),
                    timeframe_minutes=(
                        self.MORNING_TIMEFRAME_MINUTES
                    ),
                )
            )

        except Exception as exc:
            return {
                "setup": "NONE",
                "setup_direction": direction,
                "setup_state": "WAIT",
                "entry_trigger": 0.0,
                "previous_high": 0.0,
                "previous_low": 0.0,
                "setup_error": str(exc),
            }

        if not isinstance(candles, list):
            candles = []

        valid_candles = [
            candle
            for candle in candles
            if self._valid_candle(candle)
        ]

        # BCS candles-chart обычно возвращает M5:
        # newest -> oldest.
        # Setup detector работает только в chronological order:
        # oldest -> newest.
        valid_candles.sort(
            key=lambda candle: self._candle_sort_key(
                candle.get("time")
            )
        )

        if len(valid_candles) < 4:
            return self._empty_setup(direction)

        valid_candles = valid_candles[
            -self.SETUP_LOOKBACK_CANDLES:
        ]

        if direction == "LONG":
            return self._detect_long_setup(
                valid_candles
            )

        return self._detect_short_setup(
            valid_candles
        )

    # ---------------------------------------------------------
    # ANALYZE
    # ---------------------------------------------------------

    def analyze(
        self,
        ticker,
        class_code
    ):
        try:
            radar = self.radar_service.calculate(
                ticker=ticker,
                class_code=class_code
            )

        except Exception as exc:
            return {
                "version": self.VERSION,
                "ticker": ticker,
                "class_code": class_code,
                "status": "ERROR",
                "error": str(exc),
                "radar_score": 0,
                "setup": "NONE",
                "setup_direction": "NONE",
                "setup_state": "WAIT",
                "entry_trigger": 0.0,
                "previous_high": 0.0,
                "previous_low": 0.0,
            }

        if not isinstance(radar, dict):
            return {
                "version": self.VERSION,
                "ticker": ticker,
                "class_code": class_code,
                "status": "ERROR",
                "error": "Invalid radar result",
                "radar_score": 0,
                "setup": "NONE",
                "setup_direction": "NONE",
                "setup_state": "WAIT",
                "entry_trigger": 0.0,
                "previous_high": 0.0,
                "previous_low": 0.0,
            }

        daily = radar.get(
            "daily",
            {}
        )

        if not isinstance(daily, dict):
            daily = {}

        money = radar.get(
            "money",
            {}
        )

        if not isinstance(money, dict):
            money = {}

        trend = daily.get(
            "trend",
            {}
        )

        if not isinstance(trend, dict):
            trend = {}

        trend_score = self.calculate_trend_score(
            trend
        )

        money_score = self.calculate_money_score(
            money
        )

        radar_score = self.calculate_radar_score(
            trend_score,
            money_score
        )

        direction = str(
            trend.get(
                "direction",
                "NONE"
            )
        ).upper()

        trend_state = str(
            trend.get(
                "state",
                "UNKNOWN"
            )
        ).upper()

        relative_strength = (
            self.calculate_relative_strength(
                ticker,
                class_code
            )
        )

        setup = self.calculate_morning_setup(
            ticker,
            class_code,
            direction
        )

        return {
            "version": self.VERSION,
            "ticker": ticker,
            "class_code": class_code,
            "status": "OK",
            "direction": direction,
            "trend_state": trend_state,
            "trend_days": int(
                trend.get("days", 0) or 0
            ),
            "change_percent": float(
                trend.get(
                    "change_percent",
                    0
                ) or 0
            ),
            "last_close": float(
                daily.get(
                    "last_close",
                    0
                ) or 0
            ),
            "average_daily_money": float(
                money.get(
                    "average_daily_money_volume",
                    0
                ) or 0
            ),
            "trend_score": trend_score,
            "money_score": money_score,
            "radar_score": radar_score,
            "signal": self._preliminary_signal(
                radar_score,
                direction
            ),
            "m5_money_volume_status": radar.get(
                "m5_money_volume_status",
                "UNKNOWN"
            ),

            # -------------------------------------------------
            # SETUP
            # -------------------------------------------------

            "setup": setup.get(
                "setup",
                "NONE"
            ),

            "setup_direction": setup.get(
                "setup_direction",
                direction
            ),

            "setup_state": setup.get(
                "setup_state",
                "WAIT"
            ),

            "entry_trigger": float(
                setup.get(
                    "entry_trigger",
                    0
                ) or 0
            ),

            "previous_high": float(
                setup.get(
                    "previous_high",
                    0
                ) or 0
            ),

            "previous_low": float(
                setup.get(
                    "previous_low",
                    0
                ) or 0
            ),

            # -------------------------------------------------
            # RELATIVE STRENGTH
            # -------------------------------------------------

            "relative_strength": relative_strength.get(
                "relative_strength",
                0.0
            ),

            "relative_strength_score": relative_strength.get(
                "relative_strength_score",
                50.0
            ),

            "relative_strength_signal": relative_strength.get(
                "relative_strength_signal",
                "NEUTRAL"
            ),

            "relative_strength_status": relative_strength.get(
                "status",
                "NO_DATA"
            ),

            "relative_strength_previous_date": relative_strength.get(
                "previous_date"
            ),

            "relative_strength_current_date": relative_strength.get(
                "current_date"
            ),

            "relative_strength_benchmark": relative_strength.get(
                "benchmark",
                "IMOEX2/IRUS2"
            ),
        }

    # ---------------------------------------------------------
    # SCAN
    # ---------------------------------------------------------

    def scan(
        self,
        instruments=None
    ):
        if not isinstance(
            instruments,
            dict
        ):
            raise TypeError(
                "instruments must be a dict {ticker: class_code}"
            )

        results = [
            self.analyze(
                ticker,
                class_code
            )
            for ticker, class_code
            in instruments.items()
        ]

        results.sort(
            key=lambda item: float(
                item.get(
                    "radar_score",
                    0
                ) or 0
            ),
            reverse=True
        )

        for rank, result in enumerate(
            results,
            start=1
        ):
            result["rank"] = rank

        return results

    # ---------------------------------------------------------
    # PRINT
    # ---------------------------------------------------------

    def print_results(
        self,
        results
    ):
        print()
        print("=" * 150)
        print(
            "TRADER_7_12 PRO - "
            "INSTRUMENT MORNING RADAR v0.4"
        )
        print("=" * 150)
        print()

        print(
            f"{'RANK':<5}"
            f"{'TICKER':<9}"
            f"{'DIR':<8}"
            f"{'TREND':<20}"
            f"{'DAYS':<6}"
            f"{'CHANGE':<10}"
            f"{'RADAR':<8}"
            f"{'SETUP':<18}"
            f"{'STATE':<8}"
            f"{'TRIGGER':<12}"
            f"{'RS':<9}"
            f"{'RS SCORE':<10}"
            f"{'RS SIGNAL':<12}"
            f"SIGNAL"
        )

        print("-" * 150)

        for result in results:

            print(
                f"{result.get('rank', '-'): <5}"
                f"{result.get('ticker', '-'): <9}"
                f"{result.get('direction', '-'): <8}"
                f"{result.get('trend_state', '-'): <20}"
                f"{result.get('trend_days', 0): <6}"
                f"{float(result.get('change_percent', 0) or 0):>8.2f}% "
                f"{float(result.get('radar_score', 0) or 0):>6.2f}  "
                f"{result.get('setup', '-'): <18}"
                f"{result.get('setup_state', '-'): <8}"
                f"{float(result.get('entry_trigger', 0) or 0):>10.4f}  "
                f"{float(result.get('relative_strength', 0) or 0):>8.4f} "
                f"{float(result.get('relative_strength_score', 50) or 50):>8.2f}  "
                f"{result.get('relative_strength_signal', '-'): <12}"
                f"{result.get('signal', '-')}"
            )

        print()
        print(
            "RS benchmark:",
            getattr(self, "_benchmark_name", "IMOEX2/IRUS2")
        )
        print(
            "M5 money volume: "
            "NOT USED FOR TRADING RATING"
        )
        print(
            "Setup: SPOT M5 first pullback/rebound"
        )
        print("=" * 150)
