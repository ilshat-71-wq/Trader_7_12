"""
Trader_7_12 Pro

Morning Radar Service
Версия 0.1

Назначение:

- единая точка Morning Radar;
- объединение MarketSessionService;
- объединение HistoryCandleService;
- объединение MorningMoneyRadarService;
- анализ последних завершённых дневных свечей;
- определение дневного направления;
- расчёт денежной активности;
- подготовка единого результата для Scanner.

ВАЖНО:

M5 volume пока НЕ используется для расчёта
денежного оборота.

Причина:
необходимо отдельно подтвердить семантику
поля volume в BCS candles-chart.

Дневные свечи BCS уже подтверждены тестом.
"""

from datetime import datetime, timedelta, timezone

from services.market_session_service import MarketSessionService
from services.history_candle_service import HistoryCandleService
from services.morning_money_radar_service import MorningMoneyRadarService


class MorningRadarService:

    VERSION = "0.1"

    DAILY_LOOKBACK_DAYS = 10

    TREND_DAYS = 3

    def __init__(self):

        self.session_service = (
            MarketSessionService()
        )

        self.history_service = (
            HistoryCandleService()
        )

        self.money_radar = (
            MorningMoneyRadarService()
        )

    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------

    def now(self):

        return self.session_service.now()

    # ---------------------------------------------------------
    # UTC RANGE
    # ---------------------------------------------------------

    def get_history_range(self):

        now_moscow = self.now()

        end_time = (
            now_moscow.astimezone(
                timezone.utc
            )
        )

        start_time = (
            end_time
            - timedelta(
                days=self.DAILY_LOOKBACK_DAYS
            )
        )

        return (
            start_time,
            end_time
        )

    # ---------------------------------------------------------
    # DAILY CANDLES
    # ---------------------------------------------------------

    def load_daily_candles(
        self,
        ticker,
        class_code
    ):

        start_time, end_time = (
            self.get_history_range()
        )

        try:

            data = (
                self.history_service.trade_service.api.get_candles(
                    ticker,
                    class_code,
                    interval="D",
                    start_time=start_time,
                    end_time=end_time
                )
            )

        except Exception as exc:

            print()
            print(
                "❌ Morning Radar daily candles error:",
                ticker,
                exc
            )

            return []

        if not isinstance(data, dict):

            return []

        bars = data.get(
            "bars",
            []
        )

        if not bars:

            return []

        candles = []

        current_date = (
            self.now().date()
        )

        for bar in bars:

            try:

                candle_time = (
                    bar.get("time")
                )

                if not candle_time:
                    continue

                candle_date = (
                    self.history_service.get_moscow_date(
                        candle_time
                    )
                )

                if candle_date is None:
                    continue

                # Текущий незавершённый день
                # никогда не участвует в daily trend.

                if candle_date >= current_date:
                    continue

                candle = {

                    "time":
                        candle_time,

                    "date":
                        candle_date.isoformat(),

                    "open":
                        float(
                            bar.get(
                                "open",
                                0
                            ) or 0
                        ),

                    "high":
                        float(
                            bar.get(
                                "high",
                                0
                            ) or 0
                        ),

                    "low":
                        float(
                            bar.get(
                                "low",
                                0
                            ) or 0
                        ),

                    "close":
                        float(
                            bar.get(
                                "close",
                                0
                            ) or 0
                        ),

                    "volume":
                        float(
                            bar.get(
                                "volume",
                                0
                            ) or 0
                        )
                }

                if candle["close"] <= 0:
                    continue

                candles.append(
                    candle
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        # BCS обычно отдаёт newest -> oldest.
        # Для анализа разворачиваем в chronological order.

        candles.sort(
            key=lambda item: item["date"]
        )

        return candles

    # ---------------------------------------------------------
    # DAILY TREND
    # ---------------------------------------------------------

    def calculate_daily_trend(
        self,
        candles,
        trend_days=None
    ):

        if trend_days is None:

            trend_days = (
                self.TREND_DAYS
            )

        if not candles:

            return {

                "direction":
                    "NEUTRAL",

                "state":
                    "NO_DATA",

                "days":
                    0,

                "change_percent":
                    0.0
            }

        selected = candles[
            -trend_days:
        ]

        if len(selected) < 2:

            return {

                "direction":
                    "NEUTRAL",

                "state":
                    "INSUFFICIENT_DATA",

                "days":
                    len(selected),

                "change_percent":
                    0.0
            }

        first_close = float(
            selected[0]["close"]
        )

        last_close = float(
            selected[-1]["close"]
        )

        if first_close <= 0:

            return {

                "direction":
                    "NEUTRAL",

                "state":
                    "INVALID_DATA",

                "days":
                    len(selected),

                "change_percent":
                    0.0
            }

        change_percent = (
            (
                last_close
                - first_close
            )
            / first_close
            * 100
        )

        positive_days = 0
        negative_days = 0

        for previous, current in zip(
            selected,
            selected[1:]
        ):

            if current["close"] > previous["close"]:

                positive_days += 1

            elif current["close"] < previous["close"]:

                negative_days += 1

        if (
            positive_days >= 2
            and change_percent > 0
        ):

            direction = "LONG"
            state = "UPTREND"

        elif (
            negative_days >= 2
            and change_percent < 0
        ):

            direction = "SHORT"
            state = "DOWNTREND"

        elif change_percent > 0:

            direction = "LONG"
            state = "WEAK_UPTREND"

        elif change_percent < 0:

            direction = "SHORT"
            state = "WEAK_DOWNTREND"

        else:

            direction = "NEUTRAL"
            state = "FLAT"

        return {

            "direction":
                direction,

            "state":
                state,

            "days":
                len(selected),

            "change_percent":
                round(
                    change_percent,
                    2
                ),

            "positive_days":
                positive_days,

            "negative_days":
                negative_days
        }

    # ---------------------------------------------------------
    # DAILY MONEY
    # ---------------------------------------------------------

    def calculate_average_daily_money(
        self,
        ticker,
        class_code,
        completed_days=5
    ):

        try:

            return (
                self.history_service.calculate_average_daily_money(
                    ticker,
                    class_code,
                    completed_days=completed_days
                )
            )

        except Exception as exc:

            print()
            print(
                "❌ Morning Radar average money error:",
                ticker,
                exc
            )

            return 0

    # ---------------------------------------------------------
    # RADAR
    # ---------------------------------------------------------

    def calculate(
        self,
        ticker,
        class_code,
        morning_money_volume=0,
        completed_days=5
    ):

        session_info = (
            self.session_service.get_session_info()
        )

        daily_candles = (
            self.load_daily_candles(
                ticker,
                class_code
            )
        )

        daily_trend = (
            self.calculate_daily_trend(
                daily_candles
            )
        )

        average_daily_money = (
            self.calculate_average_daily_money(
                ticker,
                class_code,
                completed_days=completed_days
            )
        )

        money_activity = (
            self.money_radar.calculate(
                morning_money_volume=(
                    morning_money_volume
                ),
                average_daily_money_volume=(
                    average_daily_money
                )
            )
        )

        return {

            "version":
                self.VERSION,

            "ticker":
                ticker,

            "class_code":
                class_code,

            "session":
                session_info,

            "daily": {

                "candles":
                    len(daily_candles),

                "trend":
                    daily_trend,

                "last_close":
                    (
                        daily_candles[-1]["close"]
                        if daily_candles
                        else 0
                    )
            },

            "money":
                money_activity,

            "m5_money_volume_status":
                "NOT_USED_PENDING_BCS_VOLUME_VALIDATION"
        }

    # ---------------------------------------------------------
    # PRINT
    # ---------------------------------------------------------

    def print_radar(
        self,
        radar
    ):

        print()
        print(
            "=" * 70
        )

        print(
            "MORNING RADAR"
        )

        print(
            "=" * 70
        )

        print(
            "TICKER:",
            radar.get("ticker")
        )

        print(
            "SESSION:",
            radar.get(
                "session",
                {}
            ).get("session")
        )

        daily = radar.get(
            "daily",
            {}
        )

        trend = daily.get(
            "trend",
            {}
        )

        print(
            "DAILY CANDLES:",
            daily.get("candles", 0)
        )

        print(
            "DAILY TREND:",
            trend.get("state")
        )

        print(
            "DAILY DIRECTION:",
            trend.get("direction")
        )

        print(
            "DAILY CHANGE:",
            trend.get(
                "change_percent",
                0
            ),
            "%"
        )

        money = radar.get(
            "money",
            {}
        )

        print(
            "AVERAGE DAILY MONEY:",
            money.get(
                "average_daily_money_volume",
                0
            )
        )

        print(
            "MORNING MONEY:",
            money.get(
                "morning_money_volume",
                0
            )
        )

        print(
            "MONEY RATIO:",
            money.get(
                "daily_money_ratio",
                0
            )
        )

        print(
            "MONEY STATE:",
            money.get(
                "money_activity_state"
            )
        )

        print(
            "M5 MONEY:",
            radar.get(
                "m5_money_volume_status"
            )
        )

        print(
            "=" * 70
        )
