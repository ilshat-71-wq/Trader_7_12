"""Relative strength of a BASE ASSET (SPOT) versus IMOEX2 / IRUS2.

The futures contract is never part of this calculation.
"""


class RelativeStrengthService:
    """Calculate SPOT relative strength against the market benchmark."""

    MIN_MEANINGFUL_RS_PP = 0.10

    def calculate_return(self, previous_price, current_price):
        try:
            previous_price = float(previous_price)
            current_price = float(current_price)
        except (TypeError, ValueError):
            return 0.0
        if previous_price <= 0:
            return 0.0
        return (current_price - previous_price) / previous_price * 100.0

    def calculate(self, instrument_previous, instrument_current, benchmark_previous, benchmark_current):
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

    @classmethod
    def _signal(cls, relative_strength):
        """Use the same ±0.10 pp noise floor as the production scanner."""
        try:
            rs = float(relative_strength)
        except (TypeError, ValueError):
            return "NEUTRAL"
        if rs >= cls.MIN_MEANINGFUL_RS_PP:
            return "STRONGER"
        if rs <= -cls.MIN_MEANINGFUL_RS_PP:
            return "WEAKER"
        return "NEUTRAL"
