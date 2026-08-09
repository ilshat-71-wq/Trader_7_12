"""
Trader_7_12 Pro

Final Trade Service v0.1

Назначение:

- объединение Trade Decision
- построение Trade Plan
- проверка Risk / Reward
- расчет размера позиции
- формирование финальной торговой идеи
"""

from services.trade_plan_service import TradePlanService
from services.risk_management_service import RiskManagementService
from services.trade_idea_service import TradeIdeaService


class FinalTradeService:

    def __init__(
        self,
        deposit=1_000_000,
        risk_percent=1.0,
        min_rr=1.5,
        max_position_percent=20.0
    ):

        self.version = "0.1"

        self.trade_plan_service = (
            TradePlanService()
        )

        self.risk_service = (
            RiskManagementService(
                deposit=deposit,
                risk_percent=risk_percent,
                min_rr=min_rr,
                max_position_percent=max_position_percent
            )
        )

        self.trade_idea_service = (
            TradeIdeaService()
        )


    # ---------------------------------------------------------
    # BUILD FINAL TRADE
    # ---------------------------------------------------------

    def build(
        self,
        row,
        decision
    ):

        if not decision:

            return None


        if decision.get("decision") != "TRADE":

            return None


        current_price = float(
            getattr(
                row,
                "last",
                0
            )
        )


        signal = getattr(
            row,
            "signal",
            ""
        )


        momentum_score = getattr(
            row,
            "momentum_score",
            0
        )


        trade_score = decision.get(
            "trade_score",
            0
        )


        # -----------------------------------------------------
        # Trade Plan
        # -----------------------------------------------------

        plan = self.trade_plan_service.generate_plan(

            current_price=current_price,

            signal=signal,

            momentum_score=momentum_score,

            breakout_score=0

        )


        if not plan.get("trade_plan"):

            return None


        # -----------------------------------------------------
        # RR validation
        # -----------------------------------------------------

        rr_check = self.risk_service.validate_rr(

            plan.get(
                "rr_ratio",
                0
            )

        )


        if not rr_check.get("valid"):

            return None


        # -----------------------------------------------------
        # Position size
        # -----------------------------------------------------

        instrument = getattr(
            row,
            "instrument",
            {}
        )


        if not isinstance(
            instrument,
            dict
        ):

            instrument = {}


        lot_size = instrument.get(
            "lotSize",
            getattr(
                row,
                "lot_size",
                1
            )
        )


        position = (
            self.risk_service.calculate_position_size(

                entry=plan.get(
                    "entry"
                ),

                stop_loss=plan.get(
                    "stop_loss"
                ),

                lot_size=lot_size

            )
        )


        if not position.get("valid"):

            return None


        # -----------------------------------------------------
        # Final idea object
        # -----------------------------------------------------

        item = {

            "ticker":
                getattr(
                    row,
                    "ticker",
                    ""
                ),

            "trade_plan":
                True,

            "direction":
                plan.get(
                    "direction"
                ),

            "final_signal":
                signal,

            "confidence":
                decision.get(
                    "confidence",
                    "LOW"
                ),

            "entry":
                plan.get(
                    "entry"
                ),

            "stop_loss":
                plan.get(
                    "stop_loss"
                ),

            "take_profit":
                plan.get(
                    "take_profit"
                ),

            "rr_ratio":
                plan.get(
                    "rr_ratio"
                ),

            "reasons":
                decision.get(
                    "reasons",
                    []
                ),

            "trade_score":
                trade_score,

            "rating":
                getattr(
                    row,
                    "rating",
                    0
                ),

            "momentum_score":
                momentum_score,

            "position":
                position,

            "rr_validation":
                rr_check

        }


        idea = self.trade_idea_service.generate(
            item
        )


        if not idea:

            return None


        idea["quantity"] = position.get(
            "quantity",
            0
        )

        idea["lots"] = position.get(
            "lots",
            0
        )

        idea["position_value"] = position.get(
            "position_value",
            0
        )

        idea["risk_amount"] = position.get(
            "actual_risk_amount",
            0
        )

        idea["risk_utilization"] = position.get(
            "risk_utilization",
            0
        )

        idea["trade_score"] = trade_score

        idea["rating"] = getattr(
            row,
            "rating",
            0
        )

        idea["momentum_score"] = momentum_score

        return idea


    # ---------------------------------------------------------
    # BUILD TOP TRADES
    # ---------------------------------------------------------

    def build_top(
        self,
        rows,
        decision_engine,
        limit=3
    ):

        final_trades = []


        for row in rows:

            decision = (
                decision_engine.evaluate(
                    row
                )
            )


            if decision.get(
                "decision"
            ) != "TRADE":

                continue


            idea = self.build(
                row,
                decision
            )


            if idea:

                final_trades.append(
                    idea
                )


        final_trades.sort(

            key=lambda x: (
                x.get(
                    "trade_score",
                    0
                ),

                x.get(
                    "momentum_score",
                    0
                ),

                x.get(
                    "rating",
                    0
                )

            ),

            reverse=True

        )


        return final_trades[:limit]
