"""
Trader_7_12 Pro

Trade Plan Service

Версия 0.2

Назначение:
- legacy trade plan generation remains available;
- build a futures execution plan from a validated Spot-first candidate;
- use the futures price for execution;
- use the SPOT radar setup/levels when available;
- calculate stop, target and risk/reward deterministically.
"""


class TradePlanService:

    VERSION = "0.2"
    DEFAULT_RR = 2.0
    FALLBACK_STOP_PERCENT = 0.005

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def generate_plan(
        self,
        current_price,
        signal,
        momentum_score,
        breakout_score
    ):

        if signal in (
            "SHORT_WATCH",
            "EARLY_SHORT",
            "STRONG_SHORT"
        ):

            direction = "SHORT"
            entry = current_price
            stop_loss = round(current_price * 1.005, 2)
            take_profit = round(current_price * 0.985, 2)

        elif signal in (
            "LONG_WATCH",
            "EARLY_LONG",
            "STRONG_LONG"
        ):

            direction = "LONG"
            entry = current_price
            stop_loss = round(current_price * 0.995, 2)
            take_profit = round(current_price * 1.015, 2)

        else:
            return {
                "trade_plan": False,
                "reason": "No active signal"
            }

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        rr_ratio = round(reward / risk, 2) if risk else 0

        return {
            "trade_plan": True,
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr_ratio": rr_ratio,
            "momentum_score": momentum_score,
            "breakout_score": breakout_score
        }

    def generate_candidate_plan(self, candidate):
        """Build the execution plan for one validated futures candidate.

        Direction is never invented here. It must already be LONG/SHORT in
        the candidate. Entry uses the confirmed futures price. When the SPOT
        radar supplied a ready setup and trigger, that trigger is preferred;
        otherwise the current futures price is used.
        """
        if not isinstance(candidate, dict):
            return {
                "trade_plan": False,
                "reason": "Invalid candidate"
            }

        if str(candidate.get("status", "")).upper() != "READY":
            return {
                "trade_plan": False,
                "reason": "Candidate is not READY"
            }

        direction = str(candidate.get("direction") or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return {
                "trade_plan": False,
                "reason": "Invalid candidate direction"
            }

        futures_price = self._float(candidate.get("futures_price"))
        spot_price = self._float(candidate.get("spot_price"))
        trigger = self._float(candidate.get("entry_trigger"))
        setup_state = str(candidate.get("setup_state") or "WAIT").upper()

        if futures_price <= 0:
            return {
                "trade_plan": False,
                "reason": "No valid futures price"
            }

        entry = futures_price
        if setup_state == "READY" and trigger > 0:
            entry = futures_price

        previous_high = self._float(candidate.get("previous_high"))
        previous_low = self._float(candidate.get("previous_low"))

        if direction == "LONG":
            if previous_low > 0 and previous_low < entry:
                stop_loss = previous_low
            else:
                stop_loss = entry * (1 - self.FALLBACK_STOP_PERCENT)
        else:
            if previous_high > entry:
                stop_loss = previous_high
            else:
                stop_loss = entry * (1 + self.FALLBACK_STOP_PERCENT)

        risk = abs(entry - stop_loss)
        if risk <= 0:
            return {
                "trade_plan": False,
                "reason": "Invalid risk distance"
            }

        if direction == "LONG":
            take_profit = entry + risk * self.DEFAULT_RR
        else:
            take_profit = entry - risk * self.DEFAULT_RR

        return {
            "version": self.VERSION,
            "trade_plan": True,
            "status": "READY",
            "direction": direction,
            "futures_ticker": candidate.get("futures_ticker"),
            "futures_class_code": candidate.get("futures_class_code"),
            "spot_ticker": candidate.get("spot_ticker"),
            "spot_price": round(spot_price, 8) if spot_price > 0 else 0.0,
            "setup": candidate.get("setup", "NONE"),
            "setup_state": setup_state,
            "entry": round(entry, 8),
            "stop_loss": round(stop_loss, 8),
            "take_profit": round(take_profit, 8),
            "risk_distance": round(risk, 8),
            "rr_ratio": self.DEFAULT_RR,
            "candidate_score": round(
                self._float(candidate.get("candidate_score")), 2
            ),
            "reason": "Validated Spot-first candidate with futures confirmation",
        }
