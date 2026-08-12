"""
Trader_7_12 Pro

Instrument Morning Radar Service
Версия 0.1

Назначение:

- прогон нескольких ликвидных инструментов через MorningRadarService
- получение единого morning radar результата
- сравнение дневного тренда
- сравнение среднего дневного денежного оборота
- предварительный ranking
- подготовка данных для будущего Relative Strength vs IMOEX

ВАЖНО:

На данном этапе M5 money volume НЕ используется
для торгового рейтинга из-за ранее обнаруженной
аномалии BCS volume.

IMOEX пока НЕ входит в итоговый score.
Relative Strength будет добавлен отдельным этапом.
"""

from services.morning_radar_service import MorningRadarService


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
    # INIT
    # ---------------------------------------------------------

    def __init__(self):

        self.radar_service = (
            MorningRadarService()
        )

    # ---------------------------------------------------------
    # TREND SCORE
    # ---------------------------------------------------------

    def calculate_trend_score(
        self,
        trend
    ):
        """
        Предварительная оценка дневного тренда.

        Это НЕ торговый сигнал.

        Цель:
        отделить выраженный тренд
        от слабого/нейтрального состояния.
        """

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

        # -----------------------------------------------------
        # DIRECTION
        # -----------------------------------------------------

        if direction == "LONG":

            score += 20

        elif direction == "SHORT":

            score += 20

        # -----------------------------------------------------
        # TREND STATE
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # TREND LENGTH
        # -----------------------------------------------------

        if days >= 5:

            score += 25

        elif days >= 4:

            score += 20

        elif days >= 3:

            score += 15

        elif days >= 2:

            score += 5

        # -----------------------------------------------------
        # PRICE CHANGE
        # -----------------------------------------------------

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
        """
        Оценка качества денежного оборота.

        Используем средний дневной оборот,
        а не сомнительный M5 volume.
        """

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
        """
        Предварительный абсолютный Radar Score.

        Максимум:
            trend_score = 100
            money_score = 50

        Итог нормализуется в диапазон 0..100.
        """

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
        """
        Полный анализ одного инструмента.
        """

        try:

            radar = self.radar_service.calculate(
                ticker=ticker,
                class_code=class_code
            )

        except Exception as exc:

            return {

                "ticker":
                    ticker,

                "class_code":
                    class_code,

                "status":
                    "ERROR",

                "error":
                    str(exc),

                "radar_score":
                    0
            }

        if not isinstance(
            radar,
            dict
        ):

            return {

                "ticker":
                    ticker,

                "class_code":
                    class_code,

                "status":
                    "ERROR",

                "error":
                    "Invalid radar result",

                "radar_score":
                    0
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
                "PENDING_IMOEX"
        }

    # ---------------------------------------------------------
    # MULTI INSTRUMENT
    # ---------------------------------------------------------

    def scan(
        self,
        instruments=None
    ):
        """
        Анализирует несколько инструментов
        и сортирует их по radar_score.
        """

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
        """
        Читаемый вывод результатов.
        """

        print()

        print(
            "=" * 90
        )

        print(
            "TRADER_7_12 PRO - INSTRUMENT MORNING RADAR"
        )

        print(
            "=" * 90
        )

        print()

        header = (
            f"{'RANK':<5}"
            f"{'TICKER':<9}"
            f"{'DIR':<7}"
            f"{'TREND':<20}"
            f"{'DAYS':<6}"
            f"{'CHANGE':<10}"
            f"{'AVG MONEY':<18}"
            f"{'SCORE':<8}"
            f"{'SIGNAL'}"
        )

        print(header)

        print(
            "-" * 90
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
                f"{result.get('average_daily_money', 0):>15,.0f} "
                f"{result.get('radar_score', 0):>7.2f}  "
                f"{result.get('signal', '')}"
            )

        print()

        print(
            "=" * 90
        )

        print(
            "M5 MONEY VOLUME: "
            "PENDING BCS VOLUME VALIDATION"
        )

        print(
            "RELATIVE STRENGTH: "
            "PENDING IMOEX"
        )

        print(
            "=" * 90
        )
