"""
Trader_7_12 Pro

Relative Strength Service v0.1

Назначение:
- сравнение доходности инструмента с benchmark
- benchmark: IMOEXF — ближайший фьючерс на индекс Мосбиржи
- подготовка Relative Strength для VolumeScanner

Формула:

instrument_return =
    (instrument_current - instrument_previous)
    / instrument_previous * 100

benchmark_return =
    (benchmark_current - benchmark_previous)
    / benchmark_previous * 100

relative_strength =
    instrument_return - benchmark_return
"""


class RelativeStrengthService:

    def __init__(self):
        pass

    # ---------------------------------------------------------
    # RETURN
    # ---------------------------------------------------------

    def calculate_return(
        self,
        previous_price,
        current_price
    ):
        """
        Доходность инструмента в процентах.
        """

        try:
            previous_price = float(previous_price)
            current_price = float(current_price)
        except (TypeError, ValueError):
            return 0.0

        if previous_price <= 0:
            return 0.0

        return (
            (current_price - previous_price)
            / previous_price
            * 100
        )

    # ---------------------------------------------------------
    # RELATIVE STRENGTH
    # ---------------------------------------------------------

    def calculate(
        self,
        instrument_previous,
        instrument_current,
        benchmark_previous,
        benchmark_current
    ):
        """
        Сравнивает доходность инструмента с benchmark.
        """

        instrument_return = self.calculate_return(
            instrument_previous,
            instrument_current
        )

        benchmark_return = self.calculate_return(
            benchmark_previous,
            benchmark_current
        )

        relative_strength = (
            instrument_return
            - benchmark_return
        )

        score = self._score(
            relative_strength
        )

        signal = self._signal(
            relative_strength
        )

        return {
            "instrument_return": round(
                instrument_return,
                4
            ),

            "benchmark_return": round(
                benchmark_return,
                4
            ),

            "relative_strength": round(
                relative_strength,
                4
            ),

            "relative_strength_score": score,

            "relative_strength_signal": signal
        }

    # ---------------------------------------------------------
    # SCORE
    # ---------------------------------------------------------

    def _score(
        self,
        relative_strength
    ):
        """
        Нормализованный RS score 0-100.

        50 = нейтрально
        >50 = сильнее рынка
        <50 = слабее рынка
        """

        rs = float(relative_strength)

        # RS после calculate_return хранится
        # в процентных пунктах:
        #
        # +1.00 = +1%
        # -1.00 = -1%
        #
        # Нормализация:
        # +2.50% относительно benchmark -> 100
        #  0.00%                         -> 50
        # -2.50%                         -> 0

        score = 50 + (
            rs * 20
        )

        return round(
            max(
                0,
                min(
                    100,
                    score
                )
            ),
            2
        )

    # ---------------------------------------------------------
    # SIGNAL
    # ---------------------------------------------------------

    def _signal(
        self,
        relative_strength
    ):
        """
        Направление относительно benchmark.
        """

        rs = float(relative_strength)

        # RS хранится в процентных пунктах:
        # +1.00 = +1%
        # -1.00 = -1%

        # Сильная относительная сила:
        # инструмент существенно сильнее IMOEX.
        if rs >= 1.50:
            return "STRONG"

        # Положительная относительная сила.
        if rs >= 0.50:
            return "POSITIVE"

        # Сильная относительная слабость:
        # инструмент существенно слабее IMOEX.
        if rs <= -1.50:
            return "WEAK"

        # Отрицательная относительная сила.
        if rs <= -0.50:
            return "NEGATIVE"

        return "NEUTRAL"
