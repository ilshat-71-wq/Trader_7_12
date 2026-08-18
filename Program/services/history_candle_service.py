"""
Trader_7_12 Pro

History Candle Service
Версия 0.5

Назначение:

- загрузка исторических свечей BCS;
- поддержка M1/M5/M15/M30/H1/H4/D;
- перевод времени в Europe/Moscow;
- расчёт money_volume;
- расчёт среднего дневного денежного оборота;
- расчёт утреннего оборота 07:00–10:00 MSK;
- исключение текущего незавершённого дня.

ВАЖНО:

BCS возвращает время в UTC.
Внутренний анализ Trader_7_12 Pro
ведётся в Europe/Moscow.
"""

from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

from services.trade_service import TradeService
from services.candle_service import CandleService


class HistoryCandleService:

    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    DEFAULT_TIMEFRAME_MINUTES = 5

    COMPLETED_DAYS_FOR_AVERAGE = 5

    HISTORY_DAYS_TO_LOAD = 10

    MORNING_START = time(7, 0)
    MORNING_END = time(10, 0)

    TIMEFRAME_MAP = {
        1: "M1",
        5: "M5",
        15: "M15",
        30: "M30",
        60: "H1",
        240: "H4",
    }

    def __init__(self):

        self.trade_service = TradeService()

        self.candle_service = CandleService()

    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------

    def now(self):

        return datetime.now(
            self.MOSCOW_TZ
        )

    # ---------------------------------------------------------

    def to_moscow(self, value):

        if value is None:
            return None

        try:

            if isinstance(value, datetime):

                dt = value

            else:

                text = str(value).strip()

                if text.endswith("Z"):
                    text = (
                        text[:-1]
                        + "+00:00"
                    )

                dt = datetime.fromisoformat(
                    text
                )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt.astimezone(
                self.MOSCOW_TZ
            )

        except (
            TypeError,
            ValueError
        ):

            return None

    # ---------------------------------------------------------
    # UTC
    # ---------------------------------------------------------

    def to_utc_iso(self, value):

        if value is None:
            return None

        try:

            if isinstance(value, datetime):

                dt = value

            else:

                text = str(value).strip()

                if text.endswith("Z"):
                    text = (
                        text[:-1]
                        + "+00:00"
                    )

                dt = datetime.fromisoformat(
                    text
                )

            if dt.tzinfo is None:

                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            dt = dt.astimezone(
                timezone.utc
            )

            return dt.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )

        except (
            TypeError,
            ValueError
        ):

            return None

    # ---------------------------------------------------------
    # MOSCOW DATE
    # ---------------------------------------------------------

    def get_moscow_date(self, value):

        dt = self.to_moscow(value)

        if dt is None:
            return None

        return dt.date()

    # ---------------------------------------------------------
    # TIMEFRAME
    # ---------------------------------------------------------

    def get_interval(self, timeframe_minutes):

        try:

            minutes = int(
                timeframe_minutes
            )

        except (
            TypeError,
            ValueError
        ):

            minutes = (
                self.DEFAULT_TIMEFRAME_MINUTES
            )

        return self.TIMEFRAME_MAP.get(
            minutes,
            "M5"
        )

    # ---------------------------------------------------------
    # LOAD CANDLES
    # ---------------------------------------------------------

    def load(
        self,
        ticker,
        class_code,
        start_time=None,
        end_time=None,
        timeframe_minutes=5
    ):
        """
        Загружает исторические свечи BCS.

        Для дневных свечей:
            timeframe_minutes = None
            либо interval D через load_interval().

        Для внутридневных:
            1  -> M1
            5  -> M5
            15 -> M15
            30 -> M30
            60 -> H1
            240 -> H4
        """

        interval = self.get_interval(
            timeframe_minutes
        )

        return self.load_interval(
            ticker,
            class_code,
            interval,
            start_time,
            end_time
        )

    # ---------------------------------------------------------
    # LOAD INTERVAL
    # ---------------------------------------------------------

    def load_interval(
        self,
        ticker,
        class_code,
        interval,
        start_time=None,
        end_time=None
    ):
        """
        Универсальная загрузка свечей BCS.

        interval:
            M1
            M5
            M15
            M30
            H1
            H4
            D
        """

        try:

            data = self.trade_service.api.get_candles(
                ticker,
                class_code,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )

        except Exception as exc:

            print()
            print(
                "❌ History Candle load error:",
                ticker,
                interval,
                exc
            )

            return []

        if not isinstance(data, dict):
            return []

        bars = data.get(
            "bars",
            []
        )

        if not isinstance(bars, list):
            return []

        candles = []

        for bar in bars:

            if not isinstance(
                bar,
                dict
            ):
                continue

            try:

                candle = {

                    "time":
                        bar.get("time"),

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

                if (
                    candle["close"] <= 0
                    or candle["volume"] < 0
                    or not candle["time"]
                ):
                    continue

                # BCS candles-chart возвращает volume
                # уже как денежный оборот.
                # Дополнительное умножение на close
                # искажает показатель в тысячи раз.
                candle["money_volume"] = candle["volume"]

                candles.append(
                    candle
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        return candles

    # ---------------------------------------------------------
    # LOAD DAILY CANDLES
    # ---------------------------------------------------------

    def load_daily(
        self,
        ticker,
        class_code,
        start_time=None,
        end_time=None
    ):
        """
        Загружает дневные свечи BCS.

        BCS timeFrame для дневного периода:
            D
        """

        if end_time is None:

            end_time = (
                datetime.now(
                    timezone.utc
                )
            )

        if start_time is None:

            start_time = (
                end_time
                - timedelta(
                    days=self.HISTORY_DAYS_TO_LOAD
                )
            )

        return self.load_interval(
            ticker,
            class_code,
            "D",
            start_time,
            end_time
        )

    # ---------------------------------------------------------
    # LOAD MORNING CANDLES
    # ---------------------------------------------------------

    def load_morning_candles(
        self,
        ticker,
        class_code,
        trading_date=None,
        timeframe_minutes=5
    ):
        """
        Загружает свечи утренней сессии:

            07:00–10:00 MSK

        Если trading_date не задан,
        используется текущая московская дата.
        """

        if trading_date is None:

            trading_date = (
                self.now().date()
            )

        elif isinstance(
            trading_date,
            datetime
        ):

            moscow = self.to_moscow(
                trading_date
            )

            if moscow is None:
                return []

            trading_date = moscow.date()

        start_moscow = datetime.combine(
            trading_date,
            self.MORNING_START,
            tzinfo=self.MOSCOW_TZ
        )

        end_moscow = datetime.combine(
            trading_date,
            self.MORNING_END,
            tzinfo=self.MOSCOW_TZ
        )

        start_utc = (
            start_moscow.astimezone(
                timezone.utc
            )
        )

        end_utc = (
            end_moscow.astimezone(
                timezone.utc
            )
        )

        candles = self.load(
            ticker,
            class_code,
            start_time=start_utc,
            end_time=end_utc,
            timeframe_minutes=timeframe_minutes
        )

        result = []

        for candle in candles:

            dt = self.to_moscow(
                candle.get("time")
            )

            if dt is None:
                continue

            if (
                self.MORNING_START
                <= dt.time()
                < self.MORNING_END
            ):

                result.append(
                    candle
                )

        return result

    # ---------------------------------------------------------
    # MORNING MONEY VOLUME
    # ---------------------------------------------------------

    def calculate_morning_money_volume(
        self,
        ticker,
        class_code,
        trading_date=None,
        timeframe_minutes=5
    ):
        """
        Считает фактический денежный оборот
        утренней сессии 07:00–10:00 MSK.
        """

        candles = self.load_morning_candles(
            ticker,
            class_code,
            trading_date=trading_date,
            timeframe_minutes=timeframe_minutes
        )

        total = 0.0

        for candle in candles:

            try:

                money = float(
                    candle.get(
                        "money_volume",
                        0
                    ) or 0
                )

                if money > 0:
                    total += money

            except (
                TypeError,
                ValueError
            ):

                continue

        return round(
            total,
            2
        )

    # ---------------------------------------------------------
    # DAILY MONEY VOLUME FROM CANDLES
    # ---------------------------------------------------------

    def calculate_average_daily_money_from_candles(
        self,
        ticker,
        class_code,
        completed_days=5
    ):
        """
        Считает средний дневной денежный оборот
        по завершённым дневным свечам.

        Текущий московский день исключается.
        """

        candles = self.load_daily(
            ticker,
            class_code
        )

        if not candles:
            return 0

        current_date = (
            self.now().date()
        )

        daily = {}

        for candle in candles:

            dt = self.to_moscow(
                candle.get("time")
            )

            if dt is None:
                continue

            day = dt.date()

            if day >= current_date:
                continue

            try:

                money = float(
                    candle.get(
                        "money_volume",
                        0
                    ) or 0
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if money <= 0:
                continue

            daily[day] = (
                daily.get(
                    day,
                    0
                )
                + money
            )

        if not daily:
            return 0

        selected_days = sorted(
            daily.keys(),
            reverse=True
        )[:int(completed_days)]

        if not selected_days:
            return 0

        values = [
            daily[day]
            for day in selected_days
            if daily[day] > 0
        ]

        if not values:
            return 0

        average = (
            sum(values)
            / len(values)
        )

        return round(
            average,
            2
        )

    # ---------------------------------------------------------
    # DAILY MONEY DETAILS FROM CANDLES
    # ---------------------------------------------------------

    def get_completed_daily_money_from_candles(
        self,
        ticker,
        class_code,
        completed_days=5
    ):
        """
        Возвращает завершённые дневные обороты,
        рассчитанные непосредственно по D-свечам BCS.
        """

        candles = self.load_daily(
            ticker,
            class_code
        )

        current_date = (
            self.now().date()
        )

        daily = {}

        for candle in candles:

            dt = self.to_moscow(
                candle.get("time")
            )

            if dt is None:
                continue

            day = dt.date()

            if day >= current_date:
                continue

            try:

                money = float(
                    candle.get(
                        "money_volume",
                        0
                    ) or 0
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if money <= 0:
                continue

            daily[day] = (
                daily.get(
                    day,
                    0
                )
                + money
            )

        selected_days = sorted(
            daily.keys(),
            reverse=True
        )[:int(completed_days)]

        selected_days.sort()

        selected = {

            day.isoformat():
                round(
                    daily[day],
                    2
                )

            for day in selected_days
        }

        values = list(
            selected.values()
        )

        average = (
            sum(values)
            / len(values)
            if values
            else 0
        )

        return {

            "days":
                selected,

            "average":
                round(
                    average,
                    2
                ),

            "completed_days":
                len(values)
        }

    # ---------------------------------------------------------
    # LOAD HISTORICAL TRADES
    # ---------------------------------------------------------

    def load_trades(
        self,
        ticker,
        class_code,
        start_time,
        end_time
    ):

        return self.trade_service.load_history(
            ticker,
            class_code,
            start_time,
            end_time
        )

    # ---------------------------------------------------------
    # DAILY MONEY VOLUME FROM TRADES
    # ---------------------------------------------------------

    def calculate_daily_money_volume(
        self,
        ticker,
        class_code,
        start_time,
        end_time,
        completed_days=5
    ):
        """
        Legacy-compatible calculation from historical trades.

        Сохраняется для совместимости.
        Основной новый путь для среднего дневного
        оборота использует D-свечи BCS.
        """

        trades = self.load_trades(
            ticker,
            class_code,
            start_time,
            end_time
        )

        if not isinstance(
            trades,
            dict
        ):
            return 0

        records = trades.get(
            "records",
            []
        )

        if not records:
            return 0

        daily_money = {}

        for trade in records:

            try:

                price = float(
                    trade.get(
                        "price",
                        0
                    ) or 0
                )

                volume = float(
                    trade.get(
                        "volume",
                        trade.get(
                            "quantity",
                            0
                        )
                    ) or 0
                )

                trade_time = (
                    trade.get("time")
                    or trade.get("timestamp")
                    or trade.get("dateTime")
                )

                if (
                    price <= 0
                    or volume <= 0
                    or not trade_time
                ):
                    continue

                moscow_time = self.to_moscow(
                    trade_time
                )

                if moscow_time is None:
                    continue

                day = moscow_time.date()

                daily_money[day] = (
                    daily_money.get(
                        day,
                        0
                    )
                    + price * volume
                )

            except (
                TypeError,
                ValueError
            ):

                continue

        current_date = (
            self.now().date()
        )

        completed = {

            day: value

            for day, value
            in daily_money.items()

            if (
                day < current_date
                and value > 0
            )
        }

        selected_days = sorted(
            completed.keys(),
            reverse=True
        )[:int(completed_days)]

        values = [
            completed[day]
            for day in selected_days
            if completed[day] > 0
        ]

        if not values:
            return 0

        return round(
            sum(values) / len(values),
            2
        )

    # ---------------------------------------------------------
    # AUTOMATIC TRADE-BASED AVERAGE
    # ---------------------------------------------------------

    def calculate_average_daily_money(
        self,
        ticker,
        class_code,
        completed_days=5
    ):
        """
        Совместимый метод.

        Новый основной источник:
            D-свечи BCS.
        """

        return self.calculate_average_daily_money_from_candles(
            ticker,
            class_code,
            completed_days=completed_days
        )

    # ---------------------------------------------------------
    # DETAILS COMPATIBILITY
    # ---------------------------------------------------------

    def get_completed_daily_money(
        self,
        ticker,
        class_code,
        completed_days=5
    ):

        return self.get_completed_daily_money_from_candles(
            ticker,
            class_code,
            completed_days=completed_days
        )
