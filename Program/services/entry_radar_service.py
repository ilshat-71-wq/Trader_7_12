"""Pure decision-support state for the Entry Radar UI.

This layer does not place orders. It converts the existing Futures OI signal,
confidence, delta and flow-action fields into a compact entry-state label.
"""

class EntryRadarService:
    ENTER_MIN = 80.0
    WAIT_MIN = 65.0
    WATCH_MIN = 55.0

    @classmethod
    def state(cls, item):
        try:
            probability = float(item.get("signal_probability"))
        except (TypeError, ValueError):
            probability = None

        signal = str(item.get("signal") or "").upper()
        action = str(item.get("money_flow_position_action") or "").upper()
        zone_low = item.get("money_flow_zone_low")
        zone_high = item.get("money_flow_zone_high")
        has_zone = zone_low is not None and zone_high is not None

        if not signal or signal == "NEUTRAL" or probability is None:
            return "WATCH"
        if action == "LONG_LIQUIDATION" or action == "SHORT_COVERING" and signal == "SHORT":
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
    def direction_label(cls, item):
        signal = str(item.get("signal") or "").upper()
        return {"LONG": "🟢 LONG", "SHORT": "🔴 SHORT", "NEUTRAL": "⚪ NEUTRAL"}.get(signal, "⚪ —")

    @classmethod
    def confidence_text(cls, item):
        try:
            probability = float(item.get("signal_probability"))
        except (TypeError, ValueError):
            return "—"
        try:
            delta = float(item.get("signal_probability_delta"))
        except (TypeError, ValueError):
            delta = None
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
        try:
            low_f, high_f = float(low), float(high)
        except (TypeError, ValueError):
            return "—"
        digits = 4 if max(abs(low_f), abs(high_f)) < 100 else 0
        if max(abs(low_f), abs(high_f)) < 20:
            digits = 3
        if max(abs(low_f), abs(high_f)) >= 1000:
            digits = 0
        return f"{low_f:.{digits}f}–{high_f:.{digits}f}"
