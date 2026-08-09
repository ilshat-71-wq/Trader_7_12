"""
Trader_7_12 Pro

Risk Management Service

Версия 0.2

Назначение:

- расчет денежного риска сделки
- расчет размера позиции
- учет размера лота
- контроль максимальной позиции
- проверка Risk / Reward
- контроль фактического риска после ограничения позиции
"""

import math


class RiskManagementService:

    def __init__(
        self,
        deposit=1_000_000,
        risk_percent=1.0,
        min_rr=1.5,
        max_position_percent=20.0
    ):

        self.version = "0.2"

        self.deposit = float(deposit)

        self.risk_percent = float(
            risk_percent
        )

        self.min_rr = float(
            min_rr
        )

        self.max_position_percent = float(
            max_position_percent
        )


    # ---------------------------------------------------------
    # Target risk
    # ---------------------------------------------------------

    def calculate_risk_amount(self):

        return round(
            self.deposit *
            self.risk_percent /
            100,
            2
        )


    # ---------------------------------------------------------
    # Maximum position value
    # ---------------------------------------------------------

    def calculate_max_position_value(self):

        return round(
            self.deposit *
            self.max_position_percent /
            100,
            2
        )


    # ---------------------------------------------------------
    # Position size
    # ---------------------------------------------------------

    def calculate_position_size(
        self,
        entry,
        stop_loss,
        lot_size=1
    ):

        entry = float(entry)

        stop_loss = float(stop_loss)

        lot_size = max(
            int(lot_size),
            1
        )


        if entry <= 0:

            return {
                "valid": False,
                "reason": "Invalid entry"
            }


        if stop_loss <= 0:

            return {
                "valid": False,
                "reason": "Invalid stop"
            }


        risk_per_unit = abs(
            entry -
            stop_loss
        )


        if risk_per_unit <= 0:

            return {
                "valid": False,
                "reason": "Zero stop distance"
            }


        target_risk_amount = (
            self.calculate_risk_amount()
        )


        # Размер позиции исходя только из риска

        raw_quantity = (
            target_risk_amount /
            risk_per_unit
        )


        risk_lots = math.floor(
            raw_quantity /
            lot_size
        )


        risk_quantity = (
            risk_lots *
            lot_size
        )


        # Стоимость позиции исходя из риска

        risk_position_value = (
            risk_quantity *
            entry
        )


        max_position_value = (
            self.calculate_max_position_value()
        )


        # -----------------------------------------------------
        # Ограничение максимальной позиции
        # -----------------------------------------------------

        position_limited = False

        position_limit_reason = ""


        quantity = risk_quantity


        if risk_position_value > max_position_value:

            max_lots = math.floor(

                max_position_value /
                entry /
                lot_size

            )


            quantity = (
                max_lots *
                lot_size
            )


            position_limited = True

            position_limit_reason = (

                f"Position exceeds "
                f"{self.max_position_percent}% "
                f"of deposit"

            )


        position_value = (
            quantity *
            entry
        )


        actual_risk_amount = (
            quantity *
            risk_per_unit
        )


        risk_utilization = 0


        if target_risk_amount > 0:

            risk_utilization = (

                actual_risk_amount /
                target_risk_amount
            ) * 100


        return {

            "valid":
                quantity > 0,


            "quantity":
                quantity,


            "lots":
                quantity / lot_size,


            "lot_size":
                lot_size,


            "entry":
                entry,


            "stop_loss":
                stop_loss,


            "risk_per_unit":
                round(
                    risk_per_unit,
                    4
                ),


            "target_risk_amount":
                round(
                    target_risk_amount,
                    2
                ),


            "actual_risk_amount":
                round(
                    actual_risk_amount,
                    2
                ),


            "risk_utilization":
                round(
                    risk_utilization,
                    2
                ),


            "position_value":
                round(
                    position_value,
                    2
                ),


            "max_position_value":
                round(
                    max_position_value,
                    2
                ),


            "position_limited":
                position_limited,


            "position_limit_reason":
                position_limit_reason,


            "risk_percent":
                self.risk_percent,


            "reason":
                (
                    "OK"
                    if quantity > 0
                    else
                    "Position size below one lot"
                )
        }


    # ---------------------------------------------------------
    # Risk / Reward
    # ---------------------------------------------------------

    def validate_rr(
        self,
        rr_ratio
    ):

        rr_ratio = float(
            rr_ratio
        )


        # Защита от floating point errors

        valid = (
            round(
                rr_ratio,
                2
            )
            >=
            round(
                self.min_rr,
                2
            )
        )


        return {

            "valid":
                valid,


            "rr_ratio":
                round(
                    rr_ratio,
                    2
                ),


            "min_rr":
                round(
                    self.min_rr,
                    2
                ),


            "reason":
                (
                    "Acceptable RR"
                    if valid
                    else
                    "RR below minimum"
                )
        }
