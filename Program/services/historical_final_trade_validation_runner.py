"""Read-only historical Final Trade validation runner."""

import argparse

from services.final_trade_service import FinalTradeService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000.0
DEFAULT_CHECKPOINTS = "07:15,07:30,08:00,08:30,09:00,09:30,10:00"


def build_candidate(row):
    confirmation = row.get("futures_confirmation") or {}
    if row.get("trade_ready_time") is None or confirmation.get("status") != "OK":
        return None

    return {
        "status": "READY",
        "direction": row.get("direction"),
        "futures_ticker": row.get("futures_ticker"),
        "futures_class_code": row.get("futures_class_code"),
        "futures_expiry": row.get("futures_expiry"),
        "futures_price": row.get("futures_price", confirmation.get("last_price", 0)),
        "spot_ticker": row.get("spot_ticker"),
        "spot_class_code": row.get("spot_class_code"),
        "spot_price": row.get("spot_price", 0),
        "radar_score": row.get("radar_score", 0),
        "relative_strength": row.get("relative_strength", 0),
        "confirmation_score": confirmation.get("score", 0),
        "money_volume": confirmation.get("money_volume", 0),
        "trade_count": confirmation.get("trade_count", 0),
        "price_change_percent": confirmation.get("price_change_percent", 0),
        "candidate_score": row.get("candidate_score", 0),
        "setup": row.get("setup", "NONE"),
        "setup_state": row.get("setup_state", "WAIT"),
        "entry_trigger": row.get("entry_trigger", 0),
        "previous_high": row.get("previous_high", 0),
        "previous_low": row.get("previous_low", 0),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate Final Trade generation from historical replay data."
    )
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--min-money", type=float, default=DEFAULT_MIN_MONEY)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--checkpoints", default=DEFAULT_CHECKPOINTS)
    args = parser.parse_args()

    checkpoints = [item.strip() for item in args.checkpoints.split(",") if item.strip()]
    replay_service = HistoricalUniverseReplayService()
    rows = replay_service.replay(
        trading_date=args.date,
        min_money=args.min_money,
        checkpoints=checkpoints,
        limit=args.limit,
    )

    final_service = FinalTradeService()
    candidates = []

    print()
    print("=" * 120)
    print("FINAL TRADE HISTORICAL VALIDATION")
    print("READ ONLY — NO ORDERS")
    print("=" * 120)

    for row in rows:
        candidate = build_candidate(row)
        if candidate is None:
            continue
        candidates.append(candidate)

    trades = final_service.build_top(candidates, limit=args.limit)

    for candidate in candidates:
        ticker = candidate.get("futures_ticker") or "-"
        plan = final_service.trade_plan_service.generate_candidate_plan(candidate)
        print()
        print(f"{ticker} / {candidate.get('spot_ticker')} / {candidate.get('direction')}")
        print(f"HISTORICAL PRICE: {candidate.get('futures_price', 0)}")
        print(f"TRADE PLAN: {plan}")

    print()
    print("-" * 120)
    print(f"CANDIDATES: {len(candidates)}")
    print(f"FINAL TRADES: {len(trades)}")
    print("-" * 120)

    for trade in trades:
        print(
            f"#{trade.get('rank', '-')} "
            f"{trade.get('futures_ticker', '-')} "
            f"{trade.get('direction', '-')} "
            f"ENTRY={trade.get('entry', 0):.4f} "
            f"SL={trade.get('stop_loss', 0):.4f} "
            f"TP={trade.get('take_profit', 0):.4f} "
            f"RR={trade.get('rr_ratio', 0):.2f} "
            f"LOTS={trade.get('lots', 0)} "
            f"RISK={trade.get('actual_risk_amount', 0):.2f}"
        )

    print("=" * 120)


if __name__ == "__main__":
    main()
