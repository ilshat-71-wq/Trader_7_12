"""
Trader_7_12 Pro

Candle Service

Версия 0.4

Назначение:

- построение свечей из BCS trades
- агрегация сделок
- подготовка данных для momentum engine
- исключение незакрытой текущей свечи
"""

from datetime import datetime, timedelta, timezone


class CandleService:

    def __init__(self):

        pass

    # ---------------------------------------------------------
    # BUILD CANDLES
    # ---------------------------------------------------------

    def build_candles(
            self,
            trades,
            timeframe_minutes=5,
            closed_only=True
    ):

        if not trades:

            return []

        candles = {}

        now = datetime.now(
            timezone.utc
        )

        for trade in trades:

            try:

                price = float(
                    trade.get(
                        "price",
                        0
                    )
                )

                volume = float(
                    trade.get(
                        "volume",
                        trade.get(
                            "quantity",
                            0
                        )
                    )
                )

                time_value = trade.get(
                    "time",
                    trade.get(
                        "dateTime"
                    )
                )

                if not time_value:

                    continue

                dt = datetime.fromisoformat(
                    time_value.replace(
                        "Z",
                        "+00:00"
                    )
                )

                # -------------------------------------------------
                # NORMALIZE TIMEZONE
                # -------------------------------------------------

                if dt.tzinfo is None:

                    dt = dt.replace(
                        tzinfo=timezone.utc
                    )

                else:

                    dt = dt.astimezone(
                        timezone.utc
                    )

            except Exception:

                continue

            if price <= 0:

                continue

            # -----------------------------------------------------
            # 5-MINUTE CANDLE START
            # -----------------------------------------------------

            minute = (
                dt.minute //
                timeframe_minutes
            ) * timeframe_minutes

            candle_time = dt.replace(
                minute=minute,
                second=0,
                microsecond=0
            )

            # -----------------------------------------------------
            # CLOSED CANDLE FILTER
            # -----------------------------------------------------
            #
            # Например:
            #
            # сейчас 14:52
            #
            # свеча 14:45 -> 14:50 закрыта
            # свеча 14:50 -> 14:55 ещё формируется
            #
            # Незакрытая свеча НЕ участвует в scanner logic.
            # -----------------------------------------------------

            candle_end = (
                candle_time +
                timedelta(
                    minutes=timeframe_minutes
                )
            )

            if (
                closed_only
                and candle_end > now
            ):

                continue

            key = candle_time.isoformat()

            # -----------------------------------------------------
            # CREATE CANDLE
            # -----------------------------------------------------

            if key not in candles:

                candles[key] = {

                    "time":
                        key,

                    "open":
                        price,

                    "high":
                        price,

                    "low":
                        price,

                    "close":
                        price,

                    "volume":
                        0,

                    "money_volume":
                        0,

                    "trade_count":
                        0,

                    "price_sum":
                        0

                }

            candle = candles[key]

            # -----------------------------------------------------
            # OHLC
            # -----------------------------------------------------

            candle["high"] = max(
                candle["high"],
                price
            )

            candle["low"] = min(
                candle["low"],
                price
            )

            candle["close"] = price

            # -----------------------------------------------------
            # VOLUME
            # -----------------------------------------------------

            candle["volume"] += volume

            candle["money_volume"] += (
                price *
                volume
            )

            candle["trade_count"] += 1

            candle["price_sum"] += price

        # ---------------------------------------------------------
        # FINALIZE CANDLES
        # ---------------------------------------------------------

        result = []

        for candle in candles.values():

            if candle["trade_count"] <= 0:

                continue

            candle["average_price"] = round(
                candle["price_sum"] /
                candle["trade_count"],
                4
            )

            del candle["price_sum"]

            result.append(
                candle
            )

        # ---------------------------------------------------------
        # CHRONOLOGICAL ORDER
        # ---------------------------------------------------------

        result.sort(
            key=lambda x:
            x["time"]
        )

        return result
