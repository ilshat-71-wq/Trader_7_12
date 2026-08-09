from models.scanner_row import ScannerRow

from scanner.trade_decision_engine import TradeDecisionEngine
from services.final_trade_service import FinalTradeService


print()
print("========================================")
print("FINAL TRADE PIPELINE TEST v0.1")
print("========================================")


row = ScannerRow(

    ticker="SBER",

    last=283.94,

    change=2.5,

    volume=1_500_000,

    money_volume=150_000_000,

    rating=75,

    volume_ratio=2.5,

    volume_score=80,

    momentum_score=78,

    range_position=85,

    trade_score=85,

    direction="LONG",

    confidence="HIGH",

    reasons=[
        "Strong price movement",
        "High liquidity",
        "Strong momentum",
        "Volume confirmation"
    ],

    signal="STRONG_LONG"

)


decision_engine = TradeDecisionEngine()

final_service = FinalTradeService(

    deposit=1_000_000,

    risk_percent=1.0,

    min_rr=1.5,

    max_position_percent=20.0

)


decision = decision_engine.evaluate(
    row
)


print()
print("========== DECISION ==========")
print(decision)


idea = final_service.build(
    row,
    decision
)


print()
print("========== FINAL IDEA ==========")
print(idea)


if idea:

    print()
    print("========================================")
    print("🔥 FINAL TRADE")
    print("========================================")

    print(
        "Ticker:",
        idea.get("ticker")
    )

    print(
        "Direction:",
        idea.get("direction")
    )

    print(
        "Signal:",
        idea.get("signal")
    )

    print(
        "Confidence:",
        idea.get("confidence")
    )

    print(
        "Entry:",
        idea.get("entry")
    )

    print(
        "Stop:",
        idea.get("stop")
    )

    print(
        "Target:",
        idea.get("target")
    )

    print(
        "RR:",
        idea.get("rr")
    )

    print(
        "Quantity:",
        idea.get("quantity")
    )

    print(
        "Lots:",
        idea.get("lots")
    )

    print(
        "Position:",
        idea.get("position_value")
    )

    print(
        "Risk:",
        idea.get("risk_amount")
    )

    print(
        "Risk utilization:",
        idea.get("risk_utilization"),
        "%"

    )

    print(
        "Trade Score:",
        idea.get("trade_score")
    )

    print(
        "Momentum:",
        idea.get("momentum_score")
    )

    print(
        "Rating:",
        idea.get("rating")
    )

    print(
        "Reasons:",
        idea.get("reasons")
    )

else:

    print()
    print("⛔ NO FINAL TRADE")
