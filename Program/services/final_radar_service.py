"""FINAL RADAR — confirmation layer over existing SPOT/OI/realtime data.

This layer does not scan the market or create a new signal model. It keeps a
small in-memory history of the existing scan snapshots and only promotes a
candidate after repeated confirmation.
"""

from __future__ import annotations

from services.move_radar_service import MoveRadarService


class FinalRadarService:
    MIN_CONFIRMATIONS = 3  # first scan + two additional confirmations
    MIN_PROBABILITY = 80.0
    MAX_ATR_USED = 70.0
    MIN_DIRECTIONAL_ACCEL = 20.0
    MIN_RT_COMPONENTS = 2
    MIN_RT_SCORE = 55.0
    MAX_RESULTS = 3

    def __init__(self):
        self._day_key = None
        self._scan_no = 0
        self._history = {}
        self._realtime = {}
        self._futures = []

    @staticmethod
    def _f(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _direction(item):
        signal = str(item.get("signal") or "").upper()
        return signal if signal in {"LONG", "SHORT"} else None

    def reset(self, day_key=None):
        self._day_key = day_key
        self._scan_no = 0
        self._history = {}
        self._realtime = {}
        self._futures = []

    def record_spot_scan(self, market_map, day_key=None):
        if day_key is not None and day_key != self._day_key:
            self.reset(day_key)
        elif self._day_key is None:
            self._day_key = day_key

        self._scan_no += 1
        scan_no = self._scan_no
        candidates = MoveRadarService.candidates(market_map)
        current = {}

        for item in candidates:
            ticker = str(item.get("spot_ticker") or "").upper()
            direction = self._direction(item)
            probability = self._f(item.get("signal_probability"))
            used = self._f(item.get("atr_used_percent"))
            directional_accel = self._f(item.get("directional_acceleration"))

            if not ticker or not direction:
                continue
            # FINAL RADAR must use the same established SPOT liquidity gate
            # as Market Radar. High model confidence cannot promote an
            # illiquid instrument.
            if item.get("liquidity_gate") is not True:
                continue
            if probability is None or probability < self.MIN_PROBABILITY:
                continue
            if used is None or used > self.MAX_ATR_USED:
                continue
            if directional_accel is None or directional_accel < self.MIN_DIRECTIONAL_ACCEL:
                continue
            if item.get("move_phase") not in {"START", "DEVELOPING"}:
                continue

            previous = self._history.get(ticker)
            same_direction = previous and previous.get("direction") == direction
            consecutive = (
                previous.get("confirmations", 0) + 1
                if same_direction and previous.get("last_scan") == scan_no - 1
                else 1
            )
            current[ticker] = {
                "ticker": ticker,
                "direction": direction,
                "confirmations": consecutive,
                "last_scan": scan_no,
                "item": dict(item),
            }

        # A candidate that disappears from the strict chain loses its
        # consecutive streak. History is retained only for display/debugging.
        for ticker, state in self._history.items():
            if ticker not in current:
                state["confirmations"] = 0
                state["last_scan"] = scan_no - 1

        self._history.update(current)
        return self.final_candidates()

    def update_realtime(self, snapshot):
        ticker = str((snapshot or {}).get("ticker") or "").upper()
        if ticker:
            self._realtime[ticker] = dict(snapshot)
        return self.final_candidates()

    def update_futures(self, results):
        self._futures = [dict(x) for x in (results or [])]
        return self.final_candidates()

    def _realtime_state(self, ticker):
        snapshot = self._realtime.get(ticker) or {}
        values = []
        for key in ("book_score", "tape_score", "flow_score"):
            value = self._f(snapshot.get(key))
            if value is not None:
                values.append(value)
        if len(values) < self.MIN_RT_COMPONENTS:
            return None
        return {
            "count": len(values),
            "average": sum(values) / len(values),
            "book": self._f(snapshot.get("book_score")),
            "tape": self._f(snapshot.get("tape_score")),
            "flow": self._f(snapshot.get("flow_score")),
        }

    def _futures_state(self, ticker, direction):
        matches = [
            x for x in self._futures
            if str(x.get("underlying_ticker") or "").upper() == ticker
        ]
        if not matches:
            return {"state": "NO_MATCH"}

        valid = []
        for item in matches:
            signal = str(item.get("signal") or "").upper()
            probability = self._f(item.get("signal_probability"))
            action = str(item.get("money_flow_position_action") or "").upper()
            if action in {"LONG_LIQUIDATION", "LIQUIDATE"}:
                continue
            valid.append((signal == direction and probability is not None and probability >= 65.0, item))

        if not valid:
            return {"state": "CONFLICT"}

        confirmed, item = max(valid, key=lambda pair: self._f(pair[1].get("signal_probability")) or 0.0)
        return {
            "state": "CONFIRMED" if confirmed else "CONFLICT",
            "contract": item.get("futures_ticker") or item.get("oi_root") or "—",
            "signal": item.get("signal"),
            "probability": self._f(item.get("signal_probability")),
        }

    def final_candidates(self):
        rows = []
        for state in self._history.values():
            if state.get("last_scan") != self._scan_no:
                continue
            if state.get("confirmations", 0) < self.MIN_CONFIRMATIONS:
                continue

            item = state["item"]
            ticker = state["ticker"]
            direction = state["direction"]
            rt = self._realtime_state(ticker)
            if rt is None or rt["average"] < self.MIN_RT_SCORE:
                continue

            futures = self._futures_state(ticker, direction)
            if futures["state"] == "CONFLICT":
                continue

            rows.append({
                **item,
                "final_confirmations": state["confirmations"],
                "final_realtime": rt,
                "final_futures": futures,
            })

        def sort_key(item):
            rt = item["final_realtime"]
            prob = self._f(item.get("signal_probability")) or 0.0
            accel = abs(self._f(item.get("directional_acceleration")) or 0.0)
            return (
                -int(item.get("final_confirmations", 0)),
                -prob,
                -rt["average"],
                -accel,
            )

        return sorted(rows, key=sort_key)[: self.MAX_RESULTS]

    def status(self):
        strict = [
            x for x in self._history.values()
            if x.get("last_scan") == self._scan_no
        ]
        confirmations = max(
            (int(x.get("confirmations", 0)) for x in strict),
            default=0,
        )
        return {
            "scan_no": self._scan_no,
            "strict_candidates": len(strict),
            "max_confirmations": confirmations,
            "required_confirmations": self.MIN_CONFIRMATIONS,
            "final_count": len(self.final_candidates()),
        }
