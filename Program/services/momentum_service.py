"""
Trader_7_12 Pro

Momentum Service

Версия 0.5

Назначение:
- анализ силы свечи
- анализ объема
- анализ денежного оборота
- настоящий breakout относительно предыдущих уровней
- определение directional momentum
- подготовка данных для momentum / pullback setup

Важно:
объем и денежный оборот усиливают уже существующее направление.
Они НЕ создают направление самостоятельно.
"""


class MomentumService:

    def __init__(self):
        self.version = "0.5"

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

        # ---------------------------------------------------------
        # BREAKOUT
        # ---------------------------------------------------------

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
        # DIRECTIONAL CANDLE MOMENTUM
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
        #
        # IMPORTANT:
        #
        # Volume confirms the existing direction.
        #
        # LONG  + high volume = positive contribution
        # SHORT + high volume = negative contribution
        #
        # Volume alone cannot create direction.
        # ---------------------------------------------------------

        if close > open_price:

            if volume_ratio >= 2:
                momentum_score += 25

            elif volume_ratio >= 1.5:
                momentum_score += 15

            elif volume_ratio < 0.7:
                momentum_score -= 10

        elif close < open_price:

            if volume_ratio >= 2:
                momentum_score -= 25

            elif volume_ratio >= 1.5:
                momentum_score -= 15

            elif volume_ratio < 0.7:
                momentum_score += 10

        # ---------------------------------------------------------
        # MONEY VOLUME
        #
        # Same directional principle as ordinary volume.
        # ---------------------------------------------------------

        if close > open_price:

            if money_volume_ratio >= 2:
                momentum_score += 15

        elif close < open_price:

            if money_volume_ratio >= 2:
                momentum_score -= 15

        # ---------------------------------------------------------
        # BREAKOUT CONFIRMATION
        # ---------------------------------------------------------

        if true_breakout:

            if breakout_strength > 0:
                momentum_score += 25

            elif breakout_strength < 0:
                momentum_score -= 25

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

        # ---------------------------------------------------------
        # RESULT
        # ---------------------------------------------------------

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


if __name__ == "__main__":

    service = MomentumService()

    test_candle = {
        "open": 4020.0,
        "high": 4022.0,
        "low": 4007.0,
        "close": 4008.0,
        "volume": 2_400_000,
        "money_volume": 9_600_000_000
    }

    result = service.analyze(
        test_candle,
        average_volume=1_000_000,
        average_money_volume=4_000_000_000
    )

    print("MOMENTUM SELF TEST:")
    print(result)
