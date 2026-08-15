"""CLI runner for dynamic historical morning replay."""

import argparse

from services.historical_candidate_ranker_service import HistoricalCandidateRankerService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000
DEFAULT_CHECKPOINTS = "07:15,07:30,08:00,08:30,09:00,09:30,10:00,10:30,11:00,12:00,13:00"


def main():
    parser = argparse.ArgumentParser(
        description="Replay the dynamic liquid Futures -> SPOT universe on a completed trading day."
    )
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--min-money", type=float, default=DEFAULT_MIN_MONEY)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--checkpoints", default=DEFAULT_CHECKPOINTS)
    args = parser.parse_args()

    checkpoints = [item.strip() for item in args.checkpoints.split(",") if item.strip()]

    service = HistoricalUniverseReplayService()
    rows = service.replay(
        trading_date=args.date,
        min_money=args.min_money,
        checkpoints=checkpoints,
        limit=None,
    )
    rows = HistoricalCandidateRankerService.rank(rows, limit=args.limit)

    print()
    print("=" * 128)
    print("TRADER_7_12 PRO — HISTORICAL TOP CANDIDATES")
    print(f"DATE: {args.date} | READ ONLY — NO ORDERS")
    print("=" * 128)
    print(
        f"{'#':>3} {'FUTURES':<8} {'SPOT':<7} {'DIR':<6} "
        f"{'SCORE':>7} {'SETUP':<10} {'READY':<6} {'CONF':<6} "
        f"{'SPOT MONEY':>15} {'FUT MONEY':>15} {'CONF SCORE':>11}"
    )
    print("-" * 128)

    for item in rows:
        confirmation = item.get("futures_confirmation") or {}
        print(
            f"{item.get('rank', '-'):>3} "
            f"{str(item.get('futures_ticker', '-')):<8} "
            f"{str(item.get('spot_ticker', '-')):<7} "
            f"{str(item.get('direction', '-')):<6} "
            f"{float(item.get('candidate_score', 0) or 0):>7.2f} "
            f"{str(item.get('setup', '-')):<10} "
            f"{str(item.get('ready_time', '-')):<6} "
            f"{str(item.get('confirmation_time', '-')):<6} "
            f"{float(item.get('average_daily_money', 0) or 0):>15,.0f} "
            f"{float(item.get('futures_average_daily_money', 0) or 0):>15,.0f} "
            f"{float(confirmation.get('score', 0) or 0):>11.2f}"
        )

    print("=" * 128)
    print(f"CANDIDATES AFTER LIQUIDITY FILTER: {len(rows)}")
    print("Historical RS vs IMOEX: not loaded in this replay path; no fake RS is assigned.")
    print("Risk sizing, deposit, SL/TP, position sizing and order execution are not used.")
    print("=" * 128)


if __name__ == "__main__":
    main()
