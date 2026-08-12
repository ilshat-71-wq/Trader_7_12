"""
Trader_7_12 Pro

History Candle Service
Версия 0.4

Назначение:

- загрузка исторических свечей BCS;
- поддержка M1 / M5 / M15 / M30 / H1 / H4 / D;
- загрузка исторических сделок;
- расчёт дневного денежного оборота;
- группировка оборота по московской дате;
- исключение текущего незавершённого дня;
- расчёт среднего дневного оборота;
- подготовка данных для Morning Money Radar.

ВАЖНО:

Весь рыночный анализ Trader_7_12 Pro
ведётся в часовом поясе Europe/Moscow.

BCS возвращает время в UTC.

Для дневных свечей BCS использует:
    timeFrame = "D"

D1 / DAY / 1D не используются.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from services.trade_service import TradeService
from services.candle_service import CandleService


class HistoryCandleService:

    MOSCOW_TZ = ZoneInfo("Europe/Moscow")

    DEFAULT_TIMEFRAME_MINUTES = 5

    COMPLETED_DAYS_FOR_AVERAGE = 5

    HISTORY_DAYS_TO_LOAD = 10

    SUPPORTED_TIMEFRAMES = {
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

    def resolve_timeframe(
        self,
        timeframe_minutes=None,
        interval=None
    ):
        """
        Преобразует внутренний таймфрейм
        в BCS timeFrame.

        Поддерживаются:

            M1
            M5
            M15
            M30
            H1
            H4
            D

        Для совместимости можно передать
        либо interval, либо timeframe_minutes.
        """

        if interval:

            normalized = str(
                interval
            ).strip().upper()

            if normalized == "D":

                return "D"

            if normalized in {
                "M1",
                "M5",
                "M15",
                "M30",
                "H1",
                "H4"
            }:

                return normalized

            return "M5"

        if timeframe_minutes is None:

            timeframe_minutes = (
                self.DEFAULT_TIMEFRAME_MINUTES
            )

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

        return self.SUPPORTED_TIMEFRAMES.get(
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
        timeframe_minutes=5,
        interval=None
    ):
        """
        Загружает исторические свечи BCS.

        BCS сам агрегирует свечи.

        start_time/end_time передаются
        непосредственно в BCS API.

        Если даты не заданы, BCSAPI использует
        стандартное окно последних 4 часов.
        """

        bcs_interval = (
            self.resolve_timeframe(
                timeframe_minutes=timeframe_minutes,
                interval=interval
            )
        )

        try:

            data = self.trade_service.api.get_candles(
                ticker,
                class_code,
                interval=bcs_interval,
                start_time=start_time,
                end_time=end_time
            )

        except Exception as exc:

            print()
            print(
                "❌ History Candle load error:",
                ticker,
                bcs_interval,
                exc
            )

            return []

        if not data:
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

        for bar in bars:

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

                candle["money_volume"] = (
                    candle["volume"]
                    * candle["close"]
                )

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
    # DAILY MONEY VOLUME
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
        Рассчитывает средний дневной денежный оборот
        по последним завершённым дням.

        Алгоритм:

        1. Загружаем исторические сделки.
        2. Переводим время сделки в Moscow.
        3. Группируем сделки по московской дате.
        4. Исключаем текущий московский день.
        5. Берём последние completed_days.
        6. Считаем среднее.

        money = price * volume
        """

        trades = self.load_trades(
            ticker,
            class_code,
            start_time,
            end_time
        )

        if not trades:
            return 0

        if isinstance(trades, dict):

            records = trades.get(
                "records",
                []
            )

        else:

            records = []

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

        if not daily_money:
            return 0

        # -----------------------------------------------------
        # CURRENT MOSCOW DAY
        # -----------------------------------------------------

        current_moscow_date = (
            self.now().date()
        )

        # -----------------------------------------------------
        # COMPLETED DAYS ONLY
        # -----------------------------------------------------

        completed_daily_money = {

            day: value

            for day, value
            in daily_money.items()

            if (
                day < current_moscow_date
                and value > 0
            )
        }

        if not completed_daily_money:
            return 0

        # -----------------------------------------------------
        # LAST N COMPLETED DAYS
        # -----------------------------------------------------

        sorted_days = sorted(
            completed_daily_money.keys(),
            reverse=True
        )

        selected_days = sorted_days[
            :completed_days
        ]

        selected_days.sort()

        values = [
            completed_daily_money[day]
            for day in selected_days
            if completed_daily_money[day] > 0
        ]

        if not values:
            return 0

        # -----------------------------------------------------
        # OUTPUT
        # -----------------------------------------------------

        print()
        print(
            "========================================"
        )

        print(
            "DAILY MONEY VOLUME:",
            ticker
        )

        for day in selected_days:

            print(
                day.isoformat(),
                round(
                    completed_daily_money[day],
                    2
                )
            )

        average_daily_money = (
            sum(values)
            / len(values)
        )

        print(
            "AVERAGE DAILY MONEY:",
            round(
                average_daily_money,
                2
            )
        )

        print(
            "COMPLETED DAYS:",
            len(values)
        )

        print(
            "========================================"
        )

        return round(
            average_daily_money,
            2
        )

    # ---------------------------------------------------------
    # AUTOMATIC 5-DAY AVERAGE
    # ---------------------------------------------------------

    def calculate_average_daily_money(
        self,
        ticker,
        class_code,
        completed_days=5
    ):
        """
        Автоматически загружает историю и рассчитывает
        средний дневной денежный оборот.

        Используется московское время.
        """

        now_moscow = self.now()

        end_time = now_moscow.astimezone(
            timezone.utc
        )

        start_time = (
            end_time
            - timedelta(
                days=self.HISTORY_DAYS_TO_LOAD
            )
        )

        start_iso = (
            start_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        )

        end_iso = (
            end_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        )

        return self.calculate_daily_money_volume(
            ticker,
            class_code,
            start_iso,
            end_iso,
            completed_days=completed_days
        )

    # ---------------------------------------------------------
    # DAILY MONEY DETAILS
    # ---------------------------------------------------------

    def get_completed_daily_money(
        self,
        ticker,
        class_code,
        completed_days=5
    ):
        """
        Возвращает дневные обороты и среднее:

        {
            "days": {
                "YYYY-MM-DD": value
            },
            "average": value,
            "completed_days": N
        }

        Текущий московский день исключается.
        """

        now_moscow = self.now()

        end_time = now_moscow.astimezone(
            timezone.utc
        )

        start_time = (
            end_time
            - timedelta(
                days=self.HISTORY_DAYS_TO_LOAD
            )
        )

        trades = self.load_trades(
            ticker,
            class_code,
            start_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            ),
            end_time.strftime(
                "%Y-%m-%dT%H:%M:%S.000Z"
            )
        )

        if not isinstance(
            trades,
            dict
        ):

            return {
                "days": {},
                "average": 0,
                "completed_days": 0
            }

        records = trades.get(
            "records",
            []
        )

        if not records:

            return {
                "days": {},
                "average": 0,
                "completed_days": 0
            }

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

                dt = self.to_moscow(
                    trade_time
                )

                if dt is None:
                    continue

                day = dt.date()

                if day >= now_moscow.date():
                    continue

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

        sorted_days = sorted(
            daily_money.keys(),
            reverse=True
        )[:completed_days]

        sorted_days.sort()

        selected = {

            day.isoformat():
                round(
                    daily_money[day],
                    2
                )

            for day in sorted_days
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
