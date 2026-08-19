"""Relative strength of a BASE ASSET (SPOT) versus IMOEX2 / IRUS2.

The futures contract is never part of this calculation.
"""


class RelativeStrengthService:
    """Calculate SPOT relative strength against the market benchmark."""

    def calculate_return(self, previous_price, current_price):
        try:
            previous_price = float(previous_price)
            current_price = float(current_price)
        except (TypeError, ValueError):
            return 0.0
        if previous_price <= 0:
            return 0.0
        return (current_price - previous_price) / previous_price * 100.0

    def calculate(
        self,
        instrument_previous,
        instrument_current,
        benchmark_previous,
        benchmark_current,
    ):
        instrument_return = self.calculate_return(instrument_previous, instrument_current)
        benchmark_return = self.calculate_return(benchmark_previous, benchmark_current)
        relative_strength = instrument_return - benchmark_return
        return {
            "instrument_return": round(instrument_return, 4),
            "benchmark_return": round(benchmark_return, 4),
            "relative_strength": round(relative_strength, 4),
            "relative_strength_score": self._score(relative_strength),
            "relative_strength_signal": self._signal(relative_strength),
        }

    @staticmethod
    def _score(relative_strength):
        try:
            rs = float(relative_strength)
        except (TypeError, ValueError):
            return 50.0
        return round(max(0.0, min(100.0, 50.0 + rs * 20.0)), 2)

    @staticmethod
    def _signal(relative_strength):
        """Canonical project labels: STRONGER / WEAKER / NEUTRAL.

        Positive RS means the SPOT asset outperformed the benchmark:
        - market up + asset up more => STRONGER
        - market down + asset down less => STRONGER

        Negative RS means underperformance:
        - market up + asset up less => WEAKER
        - market down + asset down more => WEAKER
        """
        try:
            rs = float(relative_strength)
        except (TypeError, ValueError):
            return "NEUTRAL"
        if rs >= 0.20:
            return "STRONGER"
        if rs <= -0.20:
            return "WEAKER"
        return "NEUTRAL"
