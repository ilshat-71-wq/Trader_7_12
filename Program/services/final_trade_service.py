"""
Trader_7_12 Pro

Final Trade Service v0.2

Final stage of the Spot-first morning trading pipeline.

Pipeline:
SPOT Radar -> Futures Confirmation -> Trade Candidate -> Trade Plan -> Final Trade

The service does not invent direction, does not scan the market and does not
place orders. It only converts a READY validated futures candidate into a
risk-checked executable trade idea.
"""

from services.trade_plan_service import TradePlanService
from services.risk_management_service import RiskManagementService


class FinalTradeService:
    VERSION = "0.2"

    def __init__(
        self,
        deposit=1_000_000,
        risk_percent=1.0,
        min_rr=1.5,
        max_position_percent=20.0,
    ):
        self.trade_plan_service = TradePlanService()
        self.risk_service = RiskManagementService(
            deposit=deposit,
            risk_percent=risk_percent,
            min_rr=min_rr,
            max_position_percent=max_position_percent,
        )

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def build(self, candidate, lot_size=1):
        """Build one final trade from a READY candidate."""
        if not isinstance(candidate, dict):
            return None

        if str(candidate.get("status", "")).upper() != "READY":
            return None

        direction = str(candidate.get("direction") or "").upper()
        if direction not in {"LONG", "SHORT"}:
            return None

        plan = self.trade_plan_service.generate_candidate_plan(candidate)
        if not plan.get("trade_plan"):
            return None

        rr_check = self.risk_service.validate_rr(plan.get("rr_ratio", 0))
        if not rr_check.get("valid"):
            return None

        position = self.risk_service.calculate_position_size(
            entry=plan.get("entry"),
            stop_loss=plan.get("stop_loss"),
            lot_size=lot_size,
        )
        if not position.get("valid"):
            return None

        return {
            "version": self.VERSION,
            "status": "READY",
            "futures_ticker": plan.get("futures_ticker"),
            "futures_class_code": plan.get("futures_class_code"),
            "spot_ticker": plan.get("spot_ticker"),
            "direction": direction,
            "entry": plan.get("entry"),
            "stop_loss": plan.get("stop_loss"),
            "take_profit": plan.get("take_profit"),
            "rr_ratio": plan.get("rr_ratio"),
            "risk_distance": plan.get("risk_distance"),
            "quantity": position.get("quantity", 0),
            "lots": position.get("lots", 0),
            "lot_size": position.get("lot_size", 1),
            "position_value": position.get("position_value", 0),
            "target_risk_amount": position.get("target_risk_amount", 0),
            "actual_risk_amount": position.get("actual_risk_amount", 0),
            "risk_utilization": position.get("risk_utilization", 0),
            "position_limited": position.get("position_limited", False),
            "candidate_score": self._float(candidate.get("candidate_score")),
            "radar_score": self._float(candidate.get("radar_score")),
            "confirmation_score": self._float(candidate.get("confirmation_score")),
            "relative_strength": self._float(candidate.get("relative_strength")),
            "setup": candidate.get("setup", "NONE"),
            "setup_state": candidate.get("setup_state", "WAIT"),
            "reason": "READY candidate passed Trade Plan, RR and position-risk checks",
            "trade_plan": plan,
            "rr_validation": rr_check,
            "position": position,
        }

    def build_top(self, candidates, lot_sizes=None, limit=3):
        """Convert READY candidates into final trades and rank them."""
        if not isinstance(candidates, list):
            return []

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise TypeError("limit must be an integer")
        if limit < 0:
            raise ValueError("limit must be >= 0")

        lot_sizes = lot_sizes if isinstance(lot_sizes, dict) else {}
        final_trades = []

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            ticker = str(candidate.get("futures_ticker") or "").upper()
            lot_size = lot_sizes.get(ticker, candidate.get("lot_size", 1))
            trade = self.build(candidate, lot_size=lot_size)
            if trade is not None:
                final_trades.append(trade)

        final_trades.sort(
            key=lambda item: (
                item.get("candidate_score", 0),
                item.get("confirmation_score", 0),
                item.get("radar_score", 0),
            ),
            reverse=True,
        )

        for rank, trade in enumerate(final_trades, start=1):
            trade["rank"] = rank

        return final_trades[:limit]
