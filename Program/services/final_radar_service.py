"""FINAL RADAR — confirmation layer over existing SPOT/OI/realtime data.

This layer does not scan the market or create a new signal model. It keeps a
small in-memory history of existing SPOT and Futures OI snapshots and only
promotes a candidate after repeated confirmation.
"""

from __future__ import annotations

from services.move_radar_service import MoveRadarService


class FinalRadarService:
    MIN_CONFIRMATIONS = 3
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
        self._spot_scan_no = 0
        self._futures_scan_no = 0

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

    @staticmethod
    def _futures_key(item):
        return str(
            item.get("futures_ticker") or item.get("oi_root") or ""
        ).upper()

    def reset(self, day_key=None):
        self._day_key = day_key
        self._scan_no = 0
        self._history = {}
        self._realtime = {}
        self._futures = []

    def _record_candidate(self, key, direction, item, scan_no, instrument_type):
        previous = self._history.get(key)
        same_direction = previous and previous.get("direction") == direction
        consecutive = (
            previous.get("confirmations", 0) + 1
            if same_direction and previous.get("last_scan") == scan_no - 1
            else 1
        )
        return {
            "key": key,
            "ticker": str(
                item.get("spot_ticker")
                or item.get("futures_ticker")
                or key
            ).upper(),
            "instrument_type": instrument_type,
            "direction": direction,
            "confirmations": consecutive,
            "last_scan": scan_no,
            "item": dict(item),
        }

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
            # FINAL RADAR uses the same established SPOT liquidity gate as
            # Market Radar. High model confidence cannot promote illiquidity.
            if item.get("liquidity_gate") is not True:
                continue
            if probability is None or probability < self.MIN_PROBABILITY:
                continue
            if used is None or used > self.MAX_ATR_USED:
                continue
            # Move Radar already normalizes acceleration to directional
            # acceleration: positive means aligned with the model direction
            # for both LONG and SHORT.
            if directional_accel is None or directional_accel < self.MIN_DIRECTIONAL_ACCEL:
                continue
            if item.get("move_phase") not in {"START", "DEVELOPING"}:
                continue

            key = f"SPOT:{ticker}"
            current[key] = self._record_candidate(
                key, direction, item, scan_no, "SPOT"
            )

        self._spot_scan_no = scan_no
        self._merge_current(current, scan_no, "SPOT")
        return self.final_candidates()

    def record_futures_scan(self, results, day_key=None):
        if day_key is not None and day_key != self._day_key:
            self.reset(day_key)
        elif self._day_key is None:
            self._day_key = day_key

        if self._scan_no == 0:
            self._scan_no = 1
        elif self._spot_scan_no != self._scan_no:
            self._scan_no += 1
        scan_no = self._scan_no
        current = {}

        for item in results or []:
            ticker = self._futures_key(item)
            direction = self._direction(item)
            probability = self._f(item.get("signal_probability"))
            turnover = self._f(item.get("turnover_rub"))
            liquidity_state = str(item.get("money_flow_liquidity_state") or "").upper()
            money_flow_status = str(item.get("money_flow_status") or "").upper()
            action = str(item.get("money_flow_position_action") or "").upper()

            if not ticker or not direction:
                continue
            if probability is None or probability < self.MIN_PROBABILITY:
                continue
            # Use the established Futures OI / Money Flow liquidity data.
            # Do not apply the SPOT liquidity_gate to futures.
            if turnover is None or turnover <= 0:
                continue
            if money_flow_status != "AVAILABLE":
                continue
            if liquidity_state not in {"ACTIVE", "HOT"}:
                continue
            if action in {"LONG_LIQUIDATION", "LIQUIDATE"}:
                continue

            key = f"FUT:{ticker}"
            current[key] = self._record_candidate(
                key, direction, item, scan_no, "FUTURES"
            )

        self._futures_scan_no = scan_no
        self._merge_current(current, scan_no, "FUTURES")
        return self.final_candidates()

    def _merge_current(self, current, scan_no, instrument_type):
        for key, state in self._history.items():
            if state.get("instrument_type") != instrument_type:
                continue
            if key not in current:
                state["confirmations"] = 0
                state["last_scan"] = scan_no - 1
        self._history.update(current)

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
            valid.append((
                signal == direction and probability is not None and probability >= 65.0,
                item,
            ))

        if not valid:
            return {"state": "CONFLICT"}

        confirmed, item = max(
            valid,
            key=lambda pair: self._f(pair[1].get("signal_probability")) or 0.0,
        )
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
            rt = self._realtime_state(
                str(item.get("futures_ticker") if state["instrument_type"] == "FUTURES" else item.get("spot_ticker") or ticker).upper()
            )
            if rt is None or rt["average"] < self.MIN_RT_SCORE:
                continue

            futures = (
                self._futures_state(ticker, direction)
                if state["instrument_type"] == "SPOT"
                else {"state": "—"}
            )
            if futures["state"] == "CONFLICT":
                continue

            rows.append({
                **item,
                "final_instrument_type": state["instrument_type"],
                "final_ticker": ticker,
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
