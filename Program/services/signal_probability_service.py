"""Trader_7_12 Pro — real-data directional signal probability."""

from math import exp, tanh


class SignalProbabilityService:
    """
    Deterministic real-data directional model.

    IMPORTANT:
    The returned percentage is MODEL PROBABILITY, not a claim that
    the market will move with that exact probability. Calibration
    against forward outcomes will be added after historical samples
    are accumulated.
    """

    VERSION = "1.1.0"

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _sigmoid(score):
        return 1.0 / (1.0 + exp(-score))

    @staticmethod
    def _structure_score(value):
        text = str(value or "").upper()
        if any(x in text for x in ("BULL", "UP", "LONG", "POSITIVE", "GROWTH")):
            return 1.0
        if any(x in text for x in ("BEAR", "DOWN", "SHORT", "NEGATIVE", "WEAK")):
            return -1.0
        return 0.0

    def spot(self, item):
        change = self._f(item.get("change_percent"))
        rs = self._f(item.get("relative_strength"))
        accel = self._f(item.get("money_acceleration"))
        pace = self._f(item.get("money_per_minute"))
        recent_pace = self._f(item.get("recent_money_per_minute"))
        structure = self._structure_score(item.get("daily_structure"))

        momentum = tanh(change / 0.80)
        rs_signal = tanh(rs / 1.00)
        acceleration = tanh(accel / 20.0)
        liquidity = tanh(max(pace, 0.0) / 25000.0)
        recent_liquidity = tanh(max(recent_pace, 0.0) / 25000.0)

        direction = 1.0 if change > 0 else -1.0 if change < 0 else 0.0
        flow = direction * ((0.65 * liquidity) + (0.35 * recent_liquidity))

        score = (
            1.35 * momentum
            + 1.20 * rs_signal
            + 0.80 * acceleration
            + 0.75 * structure
            + 0.55 * flow
        )

        long_probability = self._sigmoid(score) * 100.0
        short_probability = 100.0 - long_probability

        if long_probability >= 55.0:
            signal = "LONG"
            probability = long_probability
        elif long_probability <= 45.0:
            signal = "SHORT"
            probability = short_probability
        else:
            signal = "NEUTRAL"
            probability = 50.0 + abs(long_probability - 50.0)

        return {
            "signal": signal,
            "probability": round(max(50.0, min(99.0, probability)), 1),
            "long_probability": round(long_probability, 1),
            "short_probability": round(short_probability, 1),
            "signal_model": self.VERSION,
        }

    def futures(self, item):
        change = self._f(item.get("change_percent"))
        oi_analysis = item.get("oi_analysis") or {}
        front_oi_change = self._f(oi_analysis.get("oi_change_percent"))

        # Near expiry, front-contract OI can fall sharply while the next
        # contract absorbs the position rollover. In that case front OI
        # alone is not a directional feature: use the combined front+next
        # curve OI change supplied by the market-data scanner.
        rollover_active = bool(item.get("rollover_active"))
        combined_oi_change = item.get("combined_oi_change_percent")
        if combined_oi_change is None:
            combined_oi_change = oi_analysis.get("combined_oi_change_percent")
        if rollover_active and combined_oi_change is not None:
            oi_change = self._f(combined_oi_change)
        else:
            oi_change = front_oi_change

        flow_delta = self._f(item.get("money_flow_delta_pct"))
        liquidity_score = self._f(item.get("money_flow_liquidity_score"))
        action = str(item.get("money_flow_position_action") or "").upper()
        flow_signal = str(item.get("money_flow_signal") or "").upper()

        price_signal = tanh(change / 2.0)
        oi_signal = tanh(oi_change / 5.0)
        flow_signal_score = tanh(flow_delta / 30.0)
        liquidity = tanh(liquidity_score / 100.0)

        action_score = {
            "LONG_BUILDUP": 1.0,
            "SHORT_COVERING": 0.75,
            "SHORT_BUILDUP": -1.0,
            "LONG_LIQUIDATION": -0.75,
        }.get(action, 0.0)

        flow_direction = {
            "ACCUMULATION": 1.0,
            "BUY_ABSORPTION": 0.85,
            "BUYER_ACTIVE": 0.70,
            "DISTRIBUTION": -1.0,
            "SELL_ABSORPTION": -0.85,
            "SELLER_ACTIVE": -0.70,
        }.get(flow_signal, 0.0)

        # The price/OI relationship remains the primary futures structure.
        # During rollover the combined curve OI is used, so a front OI drop
        # caused only by migration into the next contract cannot create a
        # false bearish signal.
        oi_price_alignment = 1.0 if change >= 0 else -1.0
        score = (
            1.15 * price_signal
            + 0.90 * oi_signal * oi_price_alignment
            + 0.95 * flow_signal_score
            + 0.70 * action_score
            + 0.35 * flow_direction
            + 0.25 * liquidity
        )

        long_probability = self._sigmoid(score) * 100.0
        short_probability = 100.0 - long_probability

        if long_probability >= 55.0:
            signal = "LONG"
            probability = long_probability
        elif long_probability <= 45.0:
            signal = "SHORT"
            probability = short_probability
        else:
            signal = "NEUTRAL"
            probability = 50.0 + abs(long_probability - 50.0)

        return {
            "signal": signal,
            "probability": round(max(50.0, min(99.0, probability)), 1),
            "long_probability": round(long_probability, 1),
            "short_probability": round(short_probability, 1),
            "signal_model": self.VERSION,
            "rollover_active": rollover_active,
            "oi_feature": "COMBINED_CURVE" if rollover_active and combined_oi_change is not None else "FRONT_CONTRACT",
        }
