from services.risk_management_service import RiskManagementService


risk = RiskManagementService(
    deposit=1_000_000,
    risk_percent=1.0,
    min_rr=1.5,
    max_position_percent=20.0
)


print()
print("================================")
print("RISK MANAGEMENT TEST v0.1")
print("================================")


print()
print("Deposit:")
print(risk.deposit)


print()
print("Risk amount:")
print(
    risk.calculate_risk_amount()
)


print()
print("Max position:")
print(
    risk.calculate_max_position_value()
)


# ---------------------------------------------------------
# SBER example
# ---------------------------------------------------------

entry = 283.94

stop_loss = 282.90

take_profit = 285.50

lot_size = 1


rr = (

    abs(
        take_profit -
        entry
    )

    /

    abs(
        entry -
        stop_loss
    )

)


print()
print("========== SBER ==========")

print(
    "Entry:",
    entry
)

print(
    "Stop:",
    stop_loss
)

print(
    "Target:",
    take_profit
)

print(
    "RR:",
    round(rr, 2)
)


print()
print("RR VALIDATION:")

print(
    risk.validate_rr(rr)
)


print()
print("POSITION:")

print(
    risk.calculate_position_size(
        entry,
        stop_loss,
        lot_size
    )
)
