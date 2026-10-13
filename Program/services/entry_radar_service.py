"""Pure decision-support state for the Entry Radar UI.

This layer does not place orders. It converts the existing Futures OI signal,
confidence, delta and flow-action fields into a compact entry-state label.
"""

from math import isfinite


class EntryRadarService:
    ENTER_MIN = 80.0
    WAIT_MIN = 65.0
    WATCH_MIN = 55.0
    MAX_SPOT_ATR_USED = 70.0

    @staticmethod
    def _number(value):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if isfinite(number) else None

    @classmethod
    def state(cls, item):
        if str(item.get("signal_status") or "").upper() == "INCOMPLETE":
            return "WATCH"
        probability = cls._number(item.get("signal_probability"))
        if probability is not None and not 0.0 <= probability <= 100.0:
            probability = None

        signal = str(item.get("signal") or "").upper()
        action = str(item.get("money_flow_position_action") or "").upper()
        zone_low = item.get("money_flow_zone_low")
        zone_high = item.get("money_flow_zone_high")
        has_zone = zone_low is not None and zone_high is not None

        # SPOT follows the real D1 -> H1 -> M5 -> M1 pipeline.
        # A synthetic money-flow zone is never required or created for SPOT.
        is_spot = str(item.get("instrument_type") or "").upper() == "SPOT" or bool(item.get("spot_ticker"))
        if is_spot:
            if signal not in {"LONG", "SHORT"} or probability is None:
                return "WATCH"
            if not item.get("daily_qualified"):
                return "WATCH"
            if item.get("liquidity_gate") is not True:
                return "WATCH"
            atr_used = cls._number(item.get("atr_used_percent"))
            if atr_used is None:
                return "WATCH"
            if atr_used > cls.MAX_SPOT_ATR_USED:
                return "AVOID"
            if str(item.get("move_phase") or "").upper() == "EXHAUSTION":
                return "AVOID"
            if probability < cls.WAIT_MIN:
                return "WATCH"
            h1_context = str(item.get("h1_level_context") or "").upper()
            h1_aligned = (
                (signal == "LONG" and h1_context == "NEAR_H1_SUPPORT")
                or (signal == "SHORT" and h1_context == "NEAR_H1_RESISTANCE")
            )
            if not h1_aligned:
                return "WATCH"
            if item.get("setup_state") not in {"WATCH", "CONFIRMED"}:
                return "WATCH"
            m1_state = str(item.get("m1_entry_state") or "UNAVAILABLE").upper()
            if m1_state == "CONFIRMED" and item.get("m1_entry_triggered"):
                return "ENTER" if probability >= cls.ENTER_MIN else "WAIT"
            if m1_state == "ARMED":
                return "WAIT"
            return "WATCH"

        if not signal or signal == "NEUTRAL" or probability is None:
            return "WATCH"
        # OI regimes are directional: long liquidation is adverse to LONG,
        # while short covering is adverse to SHORT. The opposite signal is
        # not blocked by a regime that is directionally consistent with it.
        if (
            (action == "LONG_LIQUIDATION" and signal == "LONG")
            or (action == "SHORT_COVERING" and signal == "SHORT")
        ):
            return "AVOID"
        if not has_zone:
            return "WATCH"
        if probability >= cls.ENTER_MIN:
            return "ENTER"
        if probability >= cls.WAIT_MIN:
            return "WAIT"
        if probability >= cls.WATCH_MIN:
            return "WATCH"
        return "AVOID"

    @classmethod
    def reason(cls, item):
        """Explain the gate determining the state; never implies profit certainty."""
        state = cls.state(item)
        is_spot = str(item.get("instrument_type") or "").upper() == "SPOT" or bool(item.get("spot_ticker"))
        if is_spot:
            if item.get("liquidity_gate") is not True:
                return "BLOCK: SPOT liquidity gate is not confirmed"
            atr_used = cls._number(item.get("atr_used_percent"))
            if atr_used is None:
                return "BLOCK: ATR usage is missing or invalid"
            if atr_used > cls.MAX_SPOT_ATR_USED:
                return f"BLOCK: ATR used {atr_used:.1f}% exceeds {cls.MAX_SPOT_ATR_USED:.0f}%"
            if str(item.get("move_phase") or "").upper() == "EXHAUSTION":
                return "BLOCK: move phase is EXHAUSTION"
            prob = cls._number(item.get("signal_probability"))
            if prob is not None and prob < cls.WAIT_MIN:
                return "WAIT: model score below the minimum watch threshold"
            if state == "ENTER":
                return "ENTRY CONDITIONS CONFIRMED; outcome is not guaranteed"
            if not item.get("daily_qualified"):
                return "WAIT: D1 qualification is missing"
            h1 = str(item.get("h1_level_context") or "").upper()
            if h1 not in {"NEAR_H1_SUPPORT", "NEAR_H1_RESISTANCE"}:
                return "WAIT: H1 level context is unavailable"
            m1 = str(item.get("m1_entry_state") or "UNAVAILABLE").upper()
            if m1 != "CONFIRMED" or not item.get("m1_entry_triggered"):
                return "WAIT: M1 trigger is not confirmed"
            return f"STATE: {state}"
        if state == "AVOID":
            return "BLOCK: adverse OI action or probability below watch threshold"
        if item.get("money_flow_zone_low") is None or item.get("money_flow_zone_high") is None:
            return "WAIT: real Money Flow entry zone is missing"
        if state == "ENTER":
            return "OI/FLOW conditions pass; outcome is not guaranteed"
        return f"STATE: {state}"

    @classmethod
    def direction_label(cls, item):
        signal = str(item.get("signal") or "").upper()
        return {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "NEUTRAL": "⚪ NEUTRAL"}.get(signal, "⚪ —")

    @classmethod
    def confidence_text(cls, item):
        probability = cls._number(item.get("signal_probability"))
        if probability is None:
            return "—"
        delta = cls._number(item.get("signal_probability_delta"))
        if delta is None:
            return f"{probability:.0f}%"
        arrow = "↑" if delta > 0.4 else "↓↓" if delta < -8 else "↓" if delta < -0.4 else "→"
        return f"{probability:.0f}% {arrow}"

    @classmethod
    def zone_text(cls, item):
        low = item.get("money_flow_zone_low")
        high = item.get("money_flow_zone_high")
        if low is None or high is None:
            return "—"
        low_f, high_f = cls._number(low), cls._number(high)
        if low_f is None or high_f is None or low_f > high_f:
            return "—"
        digits = 4 if max(abs(low_f), abs(high_f)) < 100 else 0
        if max(abs(low_f), abs(high_f)) < 20:
            digits = 3
        if max(abs(low_f), abs(high_f)) >= 1000:
            digits = 0
        return f"{low_f:.{digits}f}–{high_f:.{digits}f}"
