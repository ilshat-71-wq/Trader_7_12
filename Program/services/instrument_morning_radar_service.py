"""
Trader_7_12 Pro

Instrument Morning Radar Service
Версия 0.3

Назначение:

- единый spot-first Morning Radar для выбранных ликвидных акций;
- дневной тренд по завершённым D-свечам;
- средний дневной денежный оборот;
- Relative Strength относительно IMOEXF/SPBFUT;
- единый предварительный radar score;
- подготовка результата для следующего этапа scanner.

Архитектурные правила:

1. Главный benchmark: IMOEXF / SPBFUT.
2. RS не смешивается с Radar Score на этом этапе.
   RS рассчитывается и возвращается отдельно.
3. Текущий незавершённый торговый день не участвует
   в дневном тренде и Relative Strength.
4. Для D-свечей BCS торговая дата определяется по UTC.
   Это важно: timestamp завершённой дневной свечи может быть
   21:00 UTC, что соответствует следующему календарному дню
   в Москве, но сама свеча относится к предыдущей торговой дате.
5. M5 money volume не используется в торговом рейтинге.
6. Radar не открывает сделки. Он только готовит качественный
   shortlist для следующих этапов Signal/Trade Engine.
"""

from datetime import datetime, timezone

from services.morning_radar_service import MorningRadarService
from services.history_candle_service import HistoryCandleService
from services.relative_strength_service import RelativeStrengthService


class InstrumentMorningRadarService:

    VERSION = "0.3"

    DEFAULT_INSTRUMENTS = {
        "SBER": "SPBRU",
        "LKOH": "SPBRU",
        "ROSN": "SPBRU",
        "TATN": "SPBRU",
        "PLZL": "SPBRU",
        "SNGSP": "SPBRU",
        "YDEX": "SPBRU",
    }

    BENCHMARK_TICKER = "IMOEXF"
    BENCHMARK_CLASS_CODE = "SPBFUT"

    def __init__(self):
        self.radar_service = MorningRadarService()
        self.history_service = HistoryCandleService()
        self.relative_strength_service = RelativeStrengthService()
        self._benchmark_candles = None

    def load_benchmark_candles(self):
        if self._benchmark_candles is not None:
            return self._benchmark_candles

        try:
            candles = self.history_service.load_daily(
                self.BENCHMARK_TICKER,
                self.BENCHMARK_CLASS_CODE
            )
        except Exception as exc:
            print("❌ IMOEXF benchmark error:", exc)
            candles = []

        if not isinstance(candles, list):
            candles = []

        self._benchmark_candles = candles
        return candles

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

    def calculate_relative_strength_from_candles(
        self,
        instrument_candles,
        benchmark_candles=None
    ):
        """Calculate RS using the two latest common daily dates."""
        if benchmark_candles is None:
            benchmark_candles = self.load_benchmark_candles()

        instrument_map = self._build_close_map(instrument_candles)
        benchmark_map = self._build_close_map(benchmark_candles)

        common_dates = sorted(
            set(instrument_map) & set(benchmark_map)
        )

        benchmark_name = (
            f"{self.BENCHMARK_TICKER}/"
            f"{self.BENCHMARK_CLASS_CODE}"
        )

        if len(common_dates) < 2:
            return {
                "status": "NO_DATA",
                "error": "Not enough common daily candles with IMOEXF",
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

        result["status"] = "OK"
        result["previous_date"] = previous_date.isoformat()
        result["current_date"] = current_date.isoformat()
        result["benchmark"] = benchmark_name
        return result

    def calculate_relative_strength(self, ticker, class_code):
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

    @staticmethod
    def calculate_trend_score(trend):
        if not isinstance(trend, dict):
            return 0

        direction = str(trend.get("direction", "")).upper()
        state = str(trend.get("state", "")).upper()

        try:
            days = int(trend.get("days", 0) or 0)
        except (TypeError, ValueError):
            days = 0

        try:
            change_percent = float(trend.get("change_percent", 0) or 0)
        except (TypeError, ValueError):
            change_percent = 0.0

        score = 20 if direction in {"LONG", "SHORT"} else 0

        if state in {"STRONG_UPTREND", "STRONG_DOWNTREND"}:
            score += 35
        elif state in {"UPTREND", "DOWNTREND"}:
            score += 25
        elif state in {"WEAK_UPTREND", "WEAK_DOWNTREND"}:
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

    @staticmethod
    def calculate_money_score(money):
        if not isinstance(money, dict):
            return 0

        try:
            average_money = float(
                money.get("average_daily_money_volume", 0) or 0
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
    def calculate_radar_score(trend_score, money_score):
        raw_score = float(trend_score) + float(money_score)
        return round(min(raw_score / 150 * 100, 100), 2)

    @staticmethod
    def _preliminary_signal(radar_score, direction):
        if radar_score >= 70:
            if direction == "LONG":
                return "LONG_WATCH"
            if direction == "SHORT":
                return "SHORT_WATCH"
            return "WATCH"
        if radar_score >= 50:
            return "WATCH"
        return "SKIP"

    def analyze(self, ticker, class_code):
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
            }

        if not isinstance(radar, dict):
            return {
                "version": self.VERSION,
                "ticker": ticker,
                "class_code": class_code,
                "status": "ERROR",
                "error": "Invalid radar result",
                "radar_score": 0,
            }

        daily = radar.get("daily", {})
        money = radar.get("money", {})
        trend = daily.get("trend", {})

        trend_score = self.calculate_trend_score(trend)
        money_score = self.calculate_money_score(money)
        radar_score = self.calculate_radar_score(
            trend_score,
            money_score
        )

        direction = str(trend.get("direction", "NONE")).upper()
        trend_state = str(trend.get("state", "UNKNOWN")).upper()

        relative_strength = self.calculate_relative_strength(
            ticker,
            class_code
        )

        return {
            "version": self.VERSION,
            "ticker": ticker,
            "class_code": class_code,
            "status": "OK",
            "direction": direction,
            "trend_state": trend_state,
            "trend_days": int(trend.get("days", 0) or 0),
            "change_percent": float(trend.get("change_percent", 0) or 0),
            "last_close": float(daily.get("last_close", 0) or 0),
            "average_daily_money": float(
                money.get("average_daily_money_volume", 0) or 0
            ),
            "trend_score": trend_score,
            "money_score": money_score,
            "radar_score": radar_score,
            "signal": self._preliminary_signal(radar_score, direction),
            "m5_money_volume_status": radar.get(
                "m5_money_volume_status",
                "UNKNOWN"
            ),
            "relative_strength": relative_strength.get(
                "relative_strength", 0.0
            ),
            "relative_strength_score": relative_strength.get(
                "relative_strength_score", 50.0
            ),
            "relative_strength_signal": relative_strength.get(
                "relative_strength_signal", "NEUTRAL"
            ),
            "relative_strength_status": relative_strength.get(
                "status", "NO_DATA"
            ),
            "relative_strength_previous_date": relative_strength.get(
                "previous_date"
            ),
            "relative_strength_current_date": relative_strength.get(
                "current_date"
            ),
            "relative_strength_benchmark": relative_strength.get(
                "benchmark",
                "IMOEXF/SPBFUT"
            ),
        }

    def scan(self, instruments=None):
        if instruments is None:
            instruments = self.DEFAULT_INSTRUMENTS

        if not isinstance(instruments, dict):
            raise TypeError("instruments must be a dict {ticker: class_code}")

        results = [
            self.analyze(ticker, class_code)
            for ticker, class_code in instruments.items()
        ]

        results.sort(
            key=lambda item: float(item.get("radar_score", 0) or 0),
            reverse=True
        )

        for rank, result in enumerate(results, start=1):
            result["rank"] = rank

        return results

    def print_results(self, results):
        print()
        print("=" * 118)
        print("TRADER_7_12 PRO - INSTRUMENT MORNING RADAR v0.3")
        print("=" * 118)
        print()

        print(
            f"{'RANK':<5}{'TICKER':<9}{'DIR':<8}"
            f"{'TREND':<20}{'DAYS':<6}{'CHANGE':<10}"
            f"{'RADAR':<8}{'RS':<9}{'RS SCORE':<10}"
            f"{'RS SIGNAL':<12}SIGNAL"
        )
        print("-" * 118)

        for result in results:
            print(
                f"{result.get('rank', '-'): <5}"
                f"{result.get('ticker', '-'): <9}"
                f"{result.get('direction', '-'): <8}"
                f"{result.get('trend_state', '-'): <20}"
                f"{result.get('trend_days', 0): <6}"
                f"{float(result.get('change_percent', 0) or 0):>8.2f}% "
                f"{float(result.get('radar_score', 0) or 0):>6.2f}  "
                f"{float(result.get('relative_strength', 0) or 0):>8.4f} "
                f"{float(result.get('relative_strength_score', 50) or 50):>8.2f}  "
                f"{result.get('relative_strength_signal', '-'): <12}"
                f"{result.get('signal', '-')}"
            )

        print()
        print(
            "RS benchmark:",
            f"{self.BENCHMARK_TICKER}/{self.BENCHMARK_CLASS_CODE}"
        )
        print("M5 money volume: NOT USED FOR TRADING RATING")
        print("=" * 118)
