"""Trader_7_12 Pro - Stage 5 Setup Engine.

Pure SPOT price-action detection. No broker calls and no orders.
The caller supplies the candle window, so no future candles are introduced.
"""


class SetupEngine:
    VERSION = "0.1"
    MIN_IMPULSE_MOVE_PERCENT = 0.15
    MAX_PULLBACK_PERCENT = 0.80
    MIN_RANGE_CANDLES = 3
    RETEST_TOLERANCE_PERCENT = 0.20
    MAX_LOOKBACK_CANDLES = 36

    @staticmethod
    def _f(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _valid(cls, candle):
        if not isinstance(candle, dict):
            return False
        high, low, close = cls._f(candle.get("high")), cls._f(candle.get("low")), cls._f(candle.get("close"))
        return close > 0 and high >= low > 0

    @classmethod
    def _empty(cls, direction):
        return {"version": cls.VERSION, "setup": "NONE", "setup_direction": direction,
                "setup_state": "WAIT", "entry_trigger": 0.0,
                "setup_index": None, "confirmation_index": None, "level": 0.0}

    @classmethod
    def _result(cls, setup, direction, state, trigger=0.0, setup_index=None, confirmation_index=None, level=0.0):
        return {"version": cls.VERSION, "setup": setup, "setup_direction": direction,
                "setup_state": state, "entry_trigger": round(trigger, 8),
                "setup_index": setup_index, "confirmation_index": confirmation_index,
                "level": round(level, 8)}

    @classmethod
    def _pullback(cls, candles, direction):
        for i in range(1, len(candles)):
            prev, cur = candles[i - 1], candles[i]
            pc, cc = cls._f(prev.get("close")), cls._f(cur.get("close"))
            if pc <= 0:
                continue
            move = (cc - pc) / pc * 100
            impulse = move >= cls.MIN_IMPULSE_MOVE_PERCENT if direction == "LONG" else move <= -cls.MIN_IMPULSE_MOVE_PERCENT
            if not impulse:
                continue
            level = cls._f(cur.get("high")) if direction == "LONG" else cls._f(cur.get("low"))
            pulled_back = False
            for j in range(i + 1, len(candles)):
                c = candles[j]
                high, low, close = cls._f(c.get("high")), cls._f(c.get("low")), cls._f(c.get("close"))
                if direction == "LONG":
                    depth = (level - low) / level * 100 if level > 0 else 999
                    if depth > 0:
                        pulled_back = True
                    if depth > cls.MAX_PULLBACK_PERCENT:
                        return cls._result("PULLBACK", direction, "WAIT", level=level, setup_index=j)
                    if pulled_back and close > level:
                        return cls._result("PULLBACK", direction, "READY", level, j, j, level)
                else:
                    depth = (high - level) / level * 100 if level > 0 else 999
                    if depth > 0:
                        pulled_back = True
                    if depth > cls.MAX_PULLBACK_PERCENT:
                        return cls._result("PULLBACK", direction, "WAIT", level=level, setup_index=j)
                    if pulled_back and close < level:
                        return cls._result("PULLBACK", direction, "READY", level, j, j, level)
        return cls._empty(direction)

    @classmethod
    def _rebound(cls, candles, direction):
        for i in range(1, len(candles) - 1):
            prev, cur, nxt = candles[i - 1], candles[i], candles[i + 1]
            if direction == "LONG":
                level = cls._f(prev.get("low"))
                trigger = cls._f(cur.get("high"))
                if cls._f(cur.get("low")) <= level < cls._f(cur.get("close")):
                    if cls._f(nxt.get("close")) > trigger:
                        return cls._result("REBOUND", direction, "READY", trigger, i, i + 1, level)
                    return cls._result("REBOUND", direction, "WAIT", trigger, i, None, level)
            else:
                level = cls._f(prev.get("high"))
                trigger = cls._f(cur.get("low"))
                if cls._f(cur.get("high")) >= level > cls._f(cur.get("close")):
                    if cls._f(nxt.get("close")) < trigger:
                        return cls._result("REBOUND", direction, "READY", trigger, i, i + 1, level)
                    return cls._result("REBOUND", direction, "WAIT", trigger, i, None, level)
        return cls._empty(direction)

    @classmethod
    def _breakout(cls, candles, direction):
        if len(candles) <= cls.MIN_RANGE_CANDLES:
            return cls._empty(direction)
        for i in range(cls.MIN_RANGE_CANDLES, len(candles)):
            window = candles[i - cls.MIN_RANGE_CANDLES:i]
            high = max(cls._f(c.get("high")) for c in window)
            low = min(cls._f(c.get("low")) for c in window)
            close = cls._f(candles[i].get("close"))
            if direction == "LONG" and close > high:
                return cls._result("BREAKOUT", direction, "READY", close, i, i, high)
            if direction == "SHORT" and close < low:
                return cls._result("BREAKOUT", direction, "READY", close, i, i, low)
        return cls._empty(direction)

    @classmethod
    def _retest(cls, candles, direction):
        if len(candles) <= cls.MIN_RANGE_CANDLES + 1:
            return cls._empty(direction)
        for i in range(cls.MIN_RANGE_CANDLES, len(candles) - 1):
            window = candles[i - cls.MIN_RANGE_CANDLES:i]
            high = max(cls._f(c.get("high")) for c in window)
            low = min(cls._f(c.get("low")) for c in window)
            close = cls._f(candles[i].get("close"))
            level = high if direction == "LONG" else low
            broke = close > level if direction == "LONG" else close < level
            if not broke:
                continue
            for j in range(i + 1, len(candles)):
                c = candles[j]
                tolerance = level * cls.RETEST_TOLERANCE_PERCENT / 100
                touch = cls._f(c.get("low")) if direction == "LONG" else cls._f(c.get("high"))
                if abs(touch - level) > tolerance:
                    continue
                trigger = cls._f(c.get("high")) if direction == "LONG" else cls._f(c.get("low"))
                for k in range(j + 1, len(candles)):
                    continuation = cls._f(candles[k].get("close"))
                    confirmed = continuation > trigger if direction == "LONG" else continuation < trigger
                    if confirmed:
                        return cls._result("RETEST", direction, "READY", trigger, j, k, level)
                return cls._result("RETEST", direction, "WAIT", trigger, j, None, level)
        return cls._empty(direction)

    @classmethod
    def analyze(cls, candles, direction):
        direction = str(direction or "").upper()
        if direction not in {"LONG", "SHORT"}:
            raise ValueError("direction must be LONG or SHORT")
        prepared = [c for c in (candles or []) if cls._valid(c)][-cls.MAX_LOOKBACK_CANDLES:]
        if len(prepared) < 3:
            result = cls._empty(direction)
            result["candle_count"] = len(prepared)
            return result
        candidates = [
            cls._retest(prepared, direction),
            cls._rebound(prepared, direction),
            cls._pullback(prepared, direction),
            cls._breakout(prepared, direction),
        ]
        ready = [c for c in candidates if c["setup_state"] == "READY"]
        selected = min(ready, key=lambda c: c["confirmation_index"]) if ready else next((c for c in candidates if c["setup"] != "NONE"), cls._empty(direction))
        result = dict(selected)
        result["candle_count"] = len(prepared)
        result["candidates"] = candidates
        return result
