"""MOVE RADAR — phase classification over the existing SPOT market map.

This is a presentation/filter layer only. It does not create a new market scan
or alter the existing signal model. Missing data stays missing.
"""


class MoveRadarService:
    """Identify large, directionally aligned moves and classify their phase."""

    MIN_MOVE_PERCENT = 1.0
    MIN_PROBABILITY = 65.0
    START_PROBABILITY = 80.0
    START_USED_MAX = 40.0
    DEVELOPING_USED_MAX = 70.0
    LATE_USED_MAX = 100.0
    START_DIRECTIONAL_ACCEL = 20.0

    PHASE_ORDER = {
        "START": 0,
        "DEVELOPING": 1,
        "LATE": 2,
        "EXHAUSTION": 3,
    }

    @staticmethod
    def _f(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def classify(cls, item):
        signal = str(item.get("signal") or "").upper()
        change = cls._f(item.get("change_percent"))
        used = cls._f(item.get("atr_used_percent"))
        accel = cls._f(item.get("money_acceleration"))
        probability = cls._f(item.get("signal_probability"))

        if signal not in {"LONG", "SHORT"}:
            return None
        if change is None or used is None or probability is None:
            return None
        if abs(change) < cls.MIN_MOVE_PERCENT or probability < cls.MIN_PROBABILITY:
            return None

        # A move candidate must agree with its own model direction. This keeps
        # cases such as a positive price move with a SHORT model out of the
        # phase buckets until the structure resolves.
        aligned = (signal == "LONG" and change > 0) or (
            signal == "SHORT" and change < 0
        )
        if not aligned:
            return None

        directional_accel = None
        if accel is not None:
            directional_accel = accel if signal == "LONG" else -accel

        if used > cls.LATE_USED_MAX or (
            used >= 80.0 and directional_accel is not None and directional_accel < 0
        ):
            phase = "EXHAUSTION"
        elif used > cls.DEVELOPING_USED_MAX:
            phase = "LATE"
        elif (
            used <= cls.START_USED_MAX
            and probability >= cls.START_PROBABILITY
            and directional_accel is not None
            and directional_accel >= cls.START_DIRECTIONAL_ACCEL
        ):
            phase = "START"
        else:
            phase = "DEVELOPING"

        row = dict(item)
        row["move_phase"] = phase
        row["directional_acceleration"] = directional_accel
        row["move_phase_rank"] = cls.PHASE_ORDER[phase]
        return row

    @classmethod
    def candidates(cls, items):
        rows = []
        for item in items or []:
            row = cls.classify(item)
            if row is not None:
                rows.append(row)

        def sort_key(item):
            phase = cls.PHASE_ORDER[item["move_phase"]]
            prob = cls._f(item.get("signal_probability")) or 0.0
            accel = abs(cls._f(item.get("directional_acceleration")) or 0.0)
            used = cls._f(item.get("atr_used_percent")) or 0.0
            return (phase, -prob, -accel, used)

        return sorted(rows, key=sort_key)
