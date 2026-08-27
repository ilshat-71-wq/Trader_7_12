"""Canonical SPOT setup-quality calculation.

This service scores structure quality independently from setup lifecycle.
It is deterministic, network-free and never changes READY/CONFIRMED state.
"""


class SetupQualityService:
    VERSION = "0.1"

    @staticmethod
    def _f(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _bounded(cls, value):
        return round(max(0.0, min(100.0, cls._f(value))), 2)

    @classmethod
    def score(cls, setup_result, candles=None):
        """Return bounded structural quality without mutating setup state.

        The four components represent distinct evidence:
        geometry 30%, candle 25%, rejection 20%, continuation 25%.
        Missing OHLC fields never manufacture quality.
        """
        setup = str((setup_result or {}).get("setup") or "NONE").upper()
        if setup == "NONE":
            return {
                "version": cls.VERSION,
                "setup_quality_score": 0.0,
                "setup_quality_reasons": [],
                "quality_components": {},
            }

        candles = list(candles or [])
        index = (setup_result or {}).get("confirmation_index")
        if index is None:
            index = (setup_result or {}).get("setup_index")
        try:
            index = int(index)
        except (TypeError, ValueError):
            index = -1

        candle = candles[index] if 0 <= index < len(candles) else {}
        high = cls._f(candle.get("high"))
        low = cls._f(candle.get("low"))
        open_price = cls._f(candle.get("open"))
        close = cls._f(candle.get("close"))
        level = cls._f((setup_result or {}).get("level"))
        trigger = cls._f((setup_result or {}).get("entry_trigger"))

        candle_range = max(0.0, high - low)
        body = abs(close - open_price) if open_price > 0 else 0.0
        body_ratio = body / candle_range if candle_range > 0 else 0.0
        candle_score = cls._bounded(body_ratio * 100.0)

        extension = abs(trigger - level) / level * 100.0 if level > 0 and trigger > 0 else 0.0
        geometry = cls._bounded(30.0 + (extension / 0.8) * 70.0) if extension > 0 else 10.0

        upper_shadow = max(0.0, high - max(open_price, close)) if open_price > 0 else 0.0
        lower_shadow = max(0.0, min(open_price, close) - low) if open_price > 0 else 0.0
        direction = str((setup_result or {}).get("setup_direction") or "").upper()
        adverse_shadow = lower_shadow if direction == "LONG" else upper_shadow
        rejection = cls._bounded(100.0 - adverse_shadow / body * 100.0) if body > 0 else 0.0

        continuation = 100.0 if (setup_result or {}).get("confirmation_index") is not None else 25.0
        continuation = cls._bounded(continuation)

        components = {
            "geometry": geometry,
            "candle": candle_score,
            "rejection": rejection,
            "continuation": continuation,
        }
        score = round(
            geometry * 0.30
            + candle_score * 0.25
            + rejection * 0.20
            + continuation * 0.25,
            2,
        )

        reasons = []
        if geometry >= 70:
            reasons.append("clean extension through setup level")
        elif geometry < 40:
            reasons.append("shallow extension through setup level")
        if candle_score >= 60:
            reasons.append("strong confirmation candle body")
        elif candle_score < 30:
            reasons.append("weak confirmation candle body")
        if rejection >= 70:
            reasons.append("limited adverse wick")
        if continuation >= 100:
            reasons.append("continuation confirmed")
        else:
            reasons.append("continuation not yet confirmed")

        return {
            "version": cls.VERSION,
            "setup_quality_score": cls._bounded(score),
            "setup_quality_reasons": reasons,
            "quality_components": components,
        }
