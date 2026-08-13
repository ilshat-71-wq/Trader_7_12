"""
Trader_7_12 Pro

Instrument Morning Radar Service
Версия 0.2

Назначение:

- прогон нескольких ликвидных инструментов через MorningRadarService
- получение единого morning radar результата
- сравнение дневного тренда
- сравнение среднего дневного денежного оборота
- Relative Strength относительно IMOEXF
- подготовка данных для VolumeScanner

ВАЖНО:

M5 money volume НЕ используется
для торгового рейтинга из-за ранее обнаруженной
аномалии BCS volume.

Relative Strength:

benchmark = IMOEXF / SPBFUT

RS пока НЕ входит в Radar Score.
Сначала проверяем корректность расчёта отдельно.
"""

from services.morning_radar_service import MorningRadarService
from services.history_candle_service import HistoryCandleService
from services.relative_strength_service import RelativeStrengthService


class InstrumentMorningRadarService:

    # ---------------------------------------------------------
    # DEFAULT INSTRUMENTS
    # ---------------------------------------------------------

    DEFAULT_INSTRUMENTS = {
        "SBER": "SPBRU",
        "LKOH": "SPBRU",
        "ROSN": "SPBRU",
        "TATN": "SPBRU",
        "PLZL": "SPBRU",
        "SNGSP": "SPBRU",
        "YDEX": "SPBRU",
    }

    # ---------------------------------------------------------
    # IMOEXF BENCHMARK
    # ---------------------------------------------------------

    BENCHMARK_TICKER = "IMOEXF"
    BENCHMARK_CLASS_CODE = "SPBFUT"

    # ---------------------------------------------------------
    # INIT
    # ---------------------------------------------------------

    def __init__(self):

        self.radar_service = (
            MorningRadarService()
        )

        self.history_service = (
            HistoryCandleService()
        )

        self.relative_strength_service = (
            RelativeStrengthService()
        )

        self._benchmark_candles = None

    # ---------------------------------------------------------
    # LOAD BENCHMARK
    # ---------------------------------------------------------

    def load_benchmark_candles(self):

        if self._benchmark_candles is not None:

            return self._benchmark_candles

        try:

            candles = (
                self.history_service.load_daily(
                    self.BENCHMARK_TICKER,
                    self.BENCHMARK_CLASS_CODE
                )
            )

        except Exception as exc:

            print(
                "❌ IMOEXF benchmark error:",
                exc
            )

            candles = []

        if not isinstance(
            candles,
            list
        ):

            candles = []

        self._benchmark_candles = candles

        return candles

    # ---------------------------------------------------------
    # BUILD DAILY CLOSE MAP
    # ---------------------------------------------------------

    def _build_close_map(
        self,
        candles
    ):

        result = {}

        if not isinstance(
            candles,
            list
        ):

            return result

        for candle in candles:

            if not isinstance(
                candle,
                dict
            ):

                continue

            value = (
                candle.get("time")
            )

            close = (
                candle.get("close")
            )

            if not value:
                continue

            try:

                close = float(
                    close
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if close <= 0:
                continue

            day = (
                self.history_service.get_moscow_date(
                    value
                )
            )

            if day is None:
                continue

            result[day] = close

        return result

    # ---------------------------------------------------------
    # RELATIVE STRENGTH
    # ---------------------------------------------------------

    def calculate_relative_strength(
        self,
        ticker,
        class_code
    ):
        """
        Считает Relative Strength инструмента
        относительно IMOEXF.

        Используются две последние даты,
        которые одновременно присутствуют
        у инструмента и у benchmark.
        """

        try:

            instrument_candles = (
                self.history_service.load_daily(
                    ticker,
                    class_code
                )
            )

        except Exception as exc:

            return {
                "status": "ERROR",
                "error": str(exc),
                "relative_strength": 0.0,
                "relative_strength_score": 50.0,
                "relative_strength_signal": "NEUTRAL"
            }

        benchmark_candles = (
            self.load_benchmark_candles()
        )

        instrument_map = (
            self._build_close_map(
                instrument_candles
            )
        )

        benchmark_map = (
            self._build_close_map(
                benchmark_candles
            )
        )

        common_dates = sorted(
            set(instrument_map.keys())
            & set(benchmark_map.keys())
        )

        if len(common_dates) < 2:

            return {
                "status": "NO_DATA",
                "error": (
                    "Not enough common daily "
                    "candles with IMOEXF"
                ),
                "relative_strength": 0.0,
                "relative_strength_score": 50.0,
                "relative_strength_signal": "NEUTRAL"
            }

        previous_date = (
            common_dates[-2]
        )

        current_date = (
            common_dates[-1]
        )

        result = (
            self.relative_strength_service.calculate(
                instrument_previous=(
                    instrument_map[
                        previous_date
                    ]
                ),
                instrument_current=(
                    instrument_map[
                        current_date
                    ]
                ),
                benchmark_previous=(
                    benchmark_map[
                        previous_date
                    ]
                ),
                benchmark_current=(
                    benchmark_map[
                        current_date
                    ]
                )
            )
        )

        result["status"] = "OK"
        result["previous_date"] = (
            previous_date.isoformat()
        )
        result["current_date"] = (
            current_date.isoformat()
        )
        result["benchmark"] = (
            f"{self.BENCHMARK_TICKER}/"
            f"{self.BENCHMARK_CLASS_CODE}"
        )

        return result

    # ---------------------------------------------------------
    # TREND SCORE
    # ---------------------------------------------------------

    def calculate_trend_score(
        self,
        trend
    ):

        if not isinstance(
            trend,
            dict
        ):

            return 0

        direction = str(
            trend.get(
                "direction",
                ""
            )
        ).upper()

        state = str(
            trend.get(
                "state",
                ""
            )
        ).upper()

        days = int(
            trend.get(
                "days",
                0
            ) or 0
        )

        change_percent = float(
            trend.get(
                "change_percent",
                0
            ) or 0
        )

        score = 0

        if direction == "LONG":
            score += 20

        elif direction == "SHORT":
            score += 20

        if state in {
            "STRONG_UPTREND",
            "STRONG_DOWNTREND"
        }:

            score += 35

        elif state in {
            "UPTREND",
            "DOWNTREND"
        }:

            score += 25

        elif state in {
            "WEAK_UPTREND",
            "WEAK_DOWNTREND"
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

        abs_change = abs(
            change_percent
        )

        if abs_change >= 5:
            score += 20

        elif abs_change >= 3:
            score += 15

        elif abs_change >= 1:
            score += 5

        return min(
            score,
            100
        )

    # ---------------------------------------------------------
    # MONEY SCORE
    # ---------------------------------------------------------

    def calculate_money_score(
        self,
        money
    ):

        if not isinstance(
            money,
            dict
        ):

            return 0

        average_money = float(
            money.get(
                "average_daily_money_volume",
                0
            ) or 0
        )

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

    # ---------------------------------------------------------
    # RADAR SCORE
    # ---------------------------------------------------------

    def calculate_radar_score(
        self,
        trend_score,
        money_score
    ):

        raw_score = (
            float(trend_score)
            + float(money_score)
        )

        return round(
            min(
                raw_score / 150 * 100,
                100
            ),
            2
        )

    # ---------------------------------------------------------
    # SINGLE INSTRUMENT
    # ---------------------------------------------------------

    def analyze(
        self,
        ticker,
        class_code
    ):

        try:

            radar = (
                self.radar_service.calculate(
                    ticker=ticker,
                    class_code=class_code
                )
            )

        except Exception as exc:

            return {
                "ticker": ticker,
                "class_code": class_code,
                "status": "ERROR",
                "error": str(exc),
                "radar_score": 0
            }

        if not isinstance(
            radar,
            dict
        ):

            return {
                "ticker": ticker,
                "class_code": class_code,
                "status": "ERROR",
                "error": "Invalid radar result",
                "radar_score": 0
            }

        daily = radar.get(
            "daily",
            {}
        )

        money = radar.get(
            "money",
            {}
        )

        trend = daily.get(
            "trend",
            {}
        )

        trend_score = (
            self.calculate_trend_score(
                trend
            )
        )

        money_score = (
            self.calculate_money_score(
                money
            )
        )

        radar_score = (
            self.calculate_radar_score(
                trend_score,
                money_score
            )
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

        # -----------------------------------------------------
        # RELATIVE STRENGTH
        # -----------------------------------------------------

        relative_strength = (
            self.calculate_relative_strength(
                ticker,
                class_code
            )
        )

        # -----------------------------------------------------
        # PRELIMINARY SIGNAL
        # -----------------------------------------------------

        if radar_score >= 70:

            signal = (
                "LONG_WATCH"
                if direction == "LONG"
                else
                "SHORT_WATCH"
                if direction == "SHORT"
                else
                "WATCH"
            )

        elif radar_score >= 50:

            signal = "WATCH"

        else:

            signal = "SKIP"

        return {

            "ticker":
                ticker,

            "class_code":
                class_code,

            "status":
                "OK",

            "direction":
                direction,

            "trend_state":
                trend_state,

            "trend_days":
                int(
                    trend.get(
                        "days",
                        0
                    ) or 0
                ),

            "change_percent":
                float(
                    trend.get(
                        "change_percent",
                        0
                    ) or 0
                ),

            "last_close":
                float(
                    daily.get(
                        "last_close",
                        0
                    ) or 0
                ),

            "average_daily_money":
                float(
                    money.get(
                        "average_daily_money_volume",
                        0
                    ) or 0
                ),

            "trend_score":
                trend_score,

            "money_score":
                money_score,

            "radar_score":
                radar_score,

            "signal":
                signal,

            "m5_money_volume_status":
                radar.get(
                    "m5_money_volume_status",
                    "UNKNOWN"
                ),

            "relative_strength":
                relative_strength.get(
                    "relative_strength",
                    0.0
                ),

            "relative_strength_score":
                relative_strength.get(
                    "relative_strength_score",
                    50.0
                ),

            "relative_strength_signal":
                relative_strength.get(
                    "relative_strength_signal",
                    "NEUTRAL"
                ),

            "relative_strength_status":
                relative_strength.get(
                    "status",
                    "NO_DATA"
                ),

            "relative_strength_previous_date":
                relative_strength.get(
                    "previous_date"
                ),

            "relative_strength_current_date":
                relative_strength.get(
                    "current_date"
                ),

            "relative_strength_benchmark":
                relative_strength.get(
                    "benchmark",
                    "IMOEXF/SPBFUT"
                )
        }

    # ---------------------------------------------------------
    # MULTI INSTRUMENT
    # ---------------------------------------------------------

    def scan(
        self,
        instruments=None
    ):

        if instruments is None:

            instruments = (
                self.DEFAULT_INSTRUMENTS
            )

        results = []

        for ticker, class_code in (
            instruments.items()
        ):

            result = self.analyze(
                ticker,
                class_code
            )

            results.append(
                result
            )

        results.sort(
            key=lambda item: float(
                item.get(
                    "radar_score",
                    0
                ) or 0
            ),
            reverse=True
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            result["rank"] = index

        return results

    # ---------------------------------------------------------
    # PRINT
    # ---------------------------------------------------------

    def print_results(
        self,
        results
    ):

        print()
        print(
            "=" * 110
        )

        print(
            "TRADER_7_12 PRO - INSTRUMENT MORNING RADAR"
        )

        print(
            "=" * 110
        )

        print()

        header = (
            f"{'RANK':<5}"
            f"{'TICKER':<9}"
            f"{'DIR':<7}"
            f"{'TREND':<20}"
            f"{'DAYS':<6}"
            f"{'CHANGE':<10}"
            f"{'RADAR':<8}"
            f"{'RS':<9}"
            f"{'RS SCORE':<10}"
            f"{'RS SIGNAL'}"
        )

        print(header)

        print(
            "-" * 110
        )

        for result in results:

            if result.get(
                "status"
            ) != "OK":

                print(
                    f"{result.get('ticker', ''):<9}"
                    f"ERROR: "
                    f"{result.get('error', '')}"
                )

                continue

            print(
                f"{result.get('rank', 0):<5}"
                f"{result.get('ticker', ''):<9}"
                f"{result.get('direction', ''):<7}"
                f"{result.get('trend_state', ''):<20}"
                f"{result.get('trend_days', 0):<6}"
                f"{result.get('change_percent', 0):>7.2f}%   "
                f"{result.get('radar_score', 0):>6.2f}  "
                f"{result.get('relative_strength', 0):>7.2f}  "
                f"{result.get('relative_strength_score', 50):>8.2f}  "
                f"{result.get('relative_strength_signal', 'NEUTRAL')}"
            )

        print()

        print(
            "BENCHMARK: IMOEXF / SPBFUT"
        )

        print(
            "RS: ACTIVE"
        )

        print(
            "RS IS NOT INCLUDED IN RADAR SCORE YET"
        )

        print(
            "=" * 110
        )
