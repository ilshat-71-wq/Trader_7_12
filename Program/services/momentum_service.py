"""
Trader_7_12 Pro

Momentum Service

Версия 0.4

Назначение:
- анализ силы свечи
- анализ объема
- анализ денежного оборота
- настоящий breakout относительно предыдущих уровней
- определение directional momentum
- подготовка данных для momentum / pullback setup
"""


class MomentumService:

    def __init__(self):
        self.version = "0.4"

    # ---------------------------------------------------------

    def analyze(
            self,
            candle,
            average_volume=0,
            average_money_volume=0,
            previous_high=None,
            previous_low=None
    ):

        open_price = float(
            candle.get("open", 0)
        )

        high = float(
            candle.get("high", 0)
        )

        low = float(
            candle.get("low", 0)
        )

        close = float(
            candle.get("close", 0)
        )

        volume = float(
            candle.get("volume", 0)
        )

        money_volume = float(
            candle.get(
                "money_volume",
                0
            )
        )

        result = {
            "momentum_score": 0,
            "candle_power": 0,
            "range_position": 0,
            "volume_ratio": 0,
            "money_volume_ratio": 0,
            "breakout_strength": 0,
            "true_breakout": False,
            "signal": "NO_SIGNAL"
        }

        if high <= low:
            return result

        candle_range = high - low

        body = abs(
            close - open_price
        )

        candle_power = (
            body /
            candle_range
        ) * 100

        range_position = (
            (close - low) /
            candle_range
        ) * 100

        volume_ratio = 0

        if average_volume > 0:
            volume_ratio = (
                volume /
                average_volume
            )

        money_volume_ratio = 0

        if average_money_volume > 0:
            money_volume_ratio = (
                money_volume /
                average_money_volume
            )

        breakout_strength = 0
        true_breakout = False

        if previous_high is not None:

            if close > previous_high:
                breakout_strength = 100
                true_breakout = True

        if previous_low is not None:

            if close < previous_low:
                breakout_strength = -100
                true_breakout = True

        # ---------------------------------------------------------
        # MOMENTUM
        # ---------------------------------------------------------

        momentum_score = 0

        if close > open_price:

            momentum_score += candle_power / 2

            if range_position > 70:
                momentum_score += 20

        elif close < open_price:

            momentum_score -= candle_power / 2

            if range_position < 30:
                momentum_score -= 20

        # ---------------------------------------------------------
        # VOLUME
        # ---------------------------------------------------------

        if volume_ratio >= 2:

            momentum_score += 25

        elif volume_ratio >= 1.5:

            momentum_score += 15

        elif volume_ratio < 0.7:

            # Низкий текущий объём не должен полностью
            # разрушать уже сформированный momentum.
            momentum_score -= 10

        # ---------------------------------------------------------
        # MONEY VOLUME
        # ---------------------------------------------------------

        if money_volume_ratio >= 2:
            momentum_score += 15

        # ---------------------------------------------------------
        # BREAKOUT
        # ---------------------------------------------------------

        if true_breakout:

            momentum_score += (
                25
                if breakout_strength > 0
                else -25
            )

        # ---------------------------------------------------------
        # CLAMP
        # ---------------------------------------------------------

        momentum_score = int(
            max(
                min(
                    momentum_score,
                    100
                ),
                -100
            )
        )

        # ---------------------------------------------------------
        # SIGNAL
        # ---------------------------------------------------------

        signal = "NO_SIGNAL"

        if momentum_score >= 75:

            signal = "STRONG_LONG"

        elif momentum_score >= 45:

            signal = "LONG_WATCH"

        elif momentum_score <= -75:

            signal = "STRONG_SHORT"

        elif momentum_score <= -45:

            signal = "SHORT_WATCH"

        return {
            "momentum_score":
                momentum_score,

            "candle_power":
                round(
                    candle_power,
                    2
                ),

            "range_position":
                round(
                    range_position,
                    2
                ),

            "volume_ratio":
                round(
                    volume_ratio,
                    2
                ),

            "money_volume_ratio":
                round(
                    money_volume_ratio,
                    2
                ),

            "breakout_strength":
                breakout_strength,

            "true_breakout":
                true_breakout,

            "signal":
                signal
        }
