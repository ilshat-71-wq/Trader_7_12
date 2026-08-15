"""CLI runner for dynamic historical morning replay."""

import argparse

from services.historical_candidate_ranker_service import HistoricalCandidateRankerService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000
DEFAULT_CHECKPOINTS = "07:15,07:30,08:00,08:30,09:00,09:30,10:00,10:30,11:00,12:00,13:00"


def _forward_outcome(service, item, endpoint):
    """Measure realized directional move after confirmation; no risk/order logic."""
    confirmation_time = item.get("confirmation_time")
    entry_price = float(item.get("futures_price", 0) or 0)
    direction = str(item.get("direction") or "").upper()
    ticker = str(item.get("futures_ticker") or "").strip().upper()
    class_code = str(item.get("futures_class_code") or "").strip()

    if not confirmation_time or entry_price <= 0 or direction not in {"LONG", "SHORT"} or not ticker or not class_code:
        return {"available": False}

    candles = service.load_futures_candles(ticker, class_code, item.get("_trading_date"), endpoint)
    if not candles:
        return {"available": False}

    # Keep only candles from the confirmation point onward.
    start = str(confirmation_time)[:8]
    candles = [c for c in candles if str(c.get("time") or "")[11:19] >= start]
    if not candles:
        return {"available": False}

    sign = 1.0 if direction == "LONG" else -1.0
    last_price = float(candles[-1].get("close", 0) or 0)
    if last_price <= 0:
        return {"available": False}

    directional_return = (last_price - entry_price) / entry_price * 100.0 * sign
    favorable = []
    adverse = []
    for candle in candles:
        high = float(candle.get("high", 0) or 0)
        low = float(candle.get("low", 0) or 0)
        if high > 0:
            favorable.append(((high - entry_price) / entry_price * 100.0) * sign)
        if low > 0:
            adverse.append(((low - entry_price) / entry_price * 100.0) * sign)

    return {
        "available": True,
        "endpoint": endpoint,
        "last_price": round(last_price, 4),
        "directional_return_percent": round(directional_return, 2),
        "max_favorable_percent": round(max(favorable), 2) if favorable else 0.0,
        "max_adverse_percent": round(min(adverse), 2) if adverse else 0.0,
    }


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

    # Only the displayed TOP-N rows receive the short forward validation.
    for item in rows:
        item["_trading_date"] = args.date
        item["outcome_10_00"] = _forward_outcome(service, item, "10:00")
        item["outcome_13_00"] = _forward_outcome(service, item, "13:00")

    print()
    print("=" * 200)
    print("TRADER_7_12 PRO — HISTORICAL TOP CANDIDATES")
    print(f"DATE: {args.date} | READ ONLY")
    print("=" * 200)
    print(
        f"{'#':>3} {'FUTURES':<8} {'SPOT':<7} {'DIR':<6} "
        f"{'SCORE':>7} {'SETUP':<10} {'READY':<6} {'CONF':<6} "
        f"{'RS':>7} {'STATE':<9} {'EXCESS %':>10} "
        f"{'10:00 %':>9} {'10:00 MFE':>10} {'13:00 %':>9} {'13:00 MFE':>10}"
    )
    print("-" * 200)

    for item in rows:
        confirmation = item.get("futures_confirmation") or {}
        rs_data = item.get("relative_strength_data") or {}
        rs = float(item.get("relative_strength", 0) or 0)

        if not item.get("relative_strength_available"):
            rs_state = "N/A"
        elif rs > 5:
            rs_state = "STRONGER"
        elif rs < -5:
            rs_state = "WEAKER"
        else:
            rs_state = "NEUTRAL"

        out10 = item.get("outcome_10_00") or {}
        out13 = item.get("outcome_13_00") or {}

        print(
            f"{item.get('rank', '-'):>3} "
            f"{str(item.get('futures_ticker', '-')):<8} "
            f"{str(item.get('spot_ticker', '-')):<7} "
            f"{str(item.get('direction', '-')):<6} "
            f"{float(item.get('candidate_score', 0) or 0):>7.2f} "
            f"{str(item.get('setup', '-')):<10} "
            f"{str(item.get('ready_time', '-')):<6} "
            f"{str(item.get('confirmation_time', '-')):<6} "
            f"{rs:>7.2f} "
            f"{rs_state:<9} "
            f"{float(rs_data.get('excess_change_percent', 0) or 0):>10.2f} "
            f"{float(out10.get('directional_return_percent', 0) or 0):>9.2f} "
            f"{float(out10.get('max_favorable_percent', 0) or 0):>10.2f} "
            f"{float(out13.get('directional_return_percent', 0) or 0):>9.2f} "
            f"{float(out13.get('max_favorable_percent', 0) or 0):>10.2f}"
        )

    print("=" * 200)
    print(f"CANDIDATES AFTER LIQUIDITY FILTER: {len(rows)}")
    print("Historical RS: completed daily candles vs dynamically resolved IMOEX/IMOEX2 benchmark, 3-day lookback.")
    print("Forward outcome: directional futures move after confirmation; MFE is the best favorable intraday move to the endpoint.")
    print("Historical replay is read-only and does not perform portfolio or order operations.")
    print("=" * 200)


if __name__ == "__main__":
    main()
