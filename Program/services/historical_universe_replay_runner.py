"""CLI runner for dynamic historical morning replay."""

import argparse
import json
from pathlib import Path

from services.historical_candidate_ranker_service import HistoricalCandidateRankerService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000
DEFAULT_CHECKPOINTS = "07:15,07:30,08:00,08:30,09:00,09:30,10:00,10:30,11:00,12:00,13:00"


def _normalize_spot_readiness(item):
    """Make historical replay readiness explicitly SPOT-first.

    The historical service still carries legacy futures confirmation fields for
    forward-outcome analysis. They must never delay or redefine trade readiness.
    """
    ready_time = item.get("ready_time")
    spot_setup_state = str(item.get("setup_state") or "WAIT").upper()
    spot_trigger = float(item.get("entry_trigger", 0) or 0)

    item["spot_ready_time"] = ready_time
    item["spot_setup_state"] = spot_setup_state
    item["spot_entry_trigger"] = spot_trigger

    # Canonical historical trade readiness is the first valid SPOT setup.
    item["trade_ready_time"] = ready_time
    item["readiness_source"] = "SPOT"
    item["readiness_confirmed_by_futures"] = bool(item.get("futures_confirmation"))

    # Futures confirmation remains a secondary observation only.
    item["futures_confirmation_time"] = item.get("confirmation_time")
    item["futures_confirmation_status"] = str(
        (item.get("futures_confirmation") or {}).get("status") or "NO_DATA"
    ).upper()
    return item


def _forward_outcome(service, item, endpoint):
    """Measure raw and directional move after FUTURES confirmation; no order logic."""
    confirmation_time = item.get("futures_confirmation_time")
    entry_price = float(item.get("futures_price", 0) or 0)
    direction = str(item.get("direction") or "").upper()
    ticker = str(item.get("futures_ticker") or "").strip().upper()
    class_code = str(item.get("futures_class_code") or "").strip()

    if not confirmation_time or entry_price <= 0 or direction not in {"LONG", "SHORT"} or not ticker or not class_code:
        return {"available": False}

    candles = service.load_futures_candles(ticker, class_code, item.get("_trading_date"), endpoint)
    if not candles:
        return {"available": False}

    start = str(confirmation_time)[:8]
    candles = [c for c in candles if str(c.get("time") or "")[11:19] >= start]
    if not candles:
        return {"available": False}

    sign = 1.0 if direction == "LONG" else -1.0
    last_price = float(candles[-1].get("close", 0) or 0)
    if last_price <= 0:
        return {"available": False}

    raw_return = (last_price - entry_price) / entry_price * 100.0
    directional_return = raw_return * sign

    favorable = []
    adverse = []
    for candle in candles:
        high = float(candle.get("high", 0) or 0)
        low = float(candle.get("low", 0) or 0)
        if direction == "LONG":
            if high > 0:
                favorable.append((high - entry_price) / entry_price * 100.0)
            if low > 0:
                adverse.append((low - entry_price) / entry_price * 100.0)
        else:
            if low > 0:
                favorable.append((entry_price - low) / entry_price * 100.0)
            if high > 0:
                adverse.append((entry_price - high) / entry_price * 100.0)

    return {
        "available": True,
        "endpoint": endpoint,
        "last_price": round(last_price, 4),
        "raw_return_percent": round(raw_return, 2),
        "directional_return_percent": round(directional_return, 2),
        "max_favorable_percent": round(max(favorable), 2) if favorable else 0.0,
        "max_adverse_percent": round(min(adverse), 2) if adverse else 0.0,
    }


def _print_rows(rows, trading_date):
    print()
    print("=" * 220)
    print("TRADER_7_12 PRO — HISTORICAL TOP CANDIDATES")
    print(f"DATE: {trading_date} | READ ONLY")
    print("=" * 220)
    print(
        f"{'#':>3} {'FUTURES':<8} {'SPOT':<7} {'DIR':<6} "
        f"{'SCORE':>7} {'SETUP':<10} {'READY':<6} {'FUT':<6} "
        f"{'RS':>7} {'STATE':<9} {'EXCESS %':>10} "
        f"{'10 RAW %':>9} {'10 DIR %':>9} {'10 MFE':>9} "
        f"{'13 RAW %':>9} {'13 DIR %':>9} {'13 MFE':>9}"
    )
    print("-" * 220)

    for rank, item in enumerate(rows, start=1):
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
            f"{rank:>3} {str(item.get('futures_ticker', '-')):<8} "
            f"{str(item.get('spot_ticker', '-')):<7} {str(item.get('direction', '-')):<6} "
            f"{float(item.get('candidate_score', 0) or 0):>7.2f} "
            f"{str(item.get('setup', '-')):<10} {str(item.get('trade_ready_time', '-')):<6} "
            f"{str(item.get('futures_confirmation_time', '-')):<6} {rs:>7.2f} {rs_state:<9} "
            f"{float(rs_data.get('excess_change_percent', 0) or 0):>10.2f} "
            f"{float(out10.get('raw_return_percent', 0) or 0):>9.2f} "
            f"{float(out10.get('directional_return_percent', 0) or 0):>9.2f} "
            f"{float(out10.get('max_favorable_percent', 0) or 0):>9.2f} "
            f"{float(out13.get('raw_return_percent', 0) or 0):>9.2f} "
            f"{float(out13.get('directional_return_percent', 0) or 0):>9.2f} "
            f"{float(out13.get('max_favorable_percent', 0) or 0):>9.2f}"
        )
    print("=" * 220)
    print(f"CANDIDATES AFTER LIQUIDITY FILTER: {len(rows)}")


def _save_replay_results(all_results, dates, min_money):
    """Persist completed replay results for instant offline reporting."""
    output_dir = Path("Docs/historical_replay")
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": 2,
        "readiness_model": "SPOT_FIRST",
        "dates": list(dates),
        "min_money": float(min_money),
        "results": [
            {
                "trading_date": trading_date,
                "item": item,
            }
            for trading_date, item in all_results
        ],
    }

    output_path = output_dir / "latest_results.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved replay results: {output_path}")
    print(f"Saved records: {len(all_results)}")


def main():
    parser = argparse.ArgumentParser(
        description="Replay the dynamic liquid Futures -> SPOT universe on completed trading days."
    )
    parser.add_argument("--date", default=None)
    parser.add_argument("--dates", default=None, help="Comma-separated dates; one service instance is reused for the whole batch.")
    parser.add_argument("--min-money", type=float, default=DEFAULT_MIN_MONEY)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--checkpoints", default=DEFAULT_CHECKPOINTS)
    args = parser.parse_args()

    if args.date and args.dates:
        parser.error("use either --date or --dates, not both")
    dates = [item.strip() for item in (args.dates or args.date or DEFAULT_DATE).split(",") if item.strip()]
    checkpoints = [item.strip() for item in args.checkpoints.split(",") if item.strip()]

    service = HistoricalUniverseReplayService()

    # Reuse expensive BCS instrument metadata across all dates in one process.
    # The replay itself remains date-specific; only immutable metadata is cached.
    mapping_cache = service.mapping_service.load()
    service.mapping_service.load = lambda: mapping_cache
    benchmark_cache = {"loaded": False, "value": None}
    original_benchmark_loader = service.load_market_benchmark

    def cached_benchmark_loader():
        if not benchmark_cache["loaded"]:
            benchmark_cache["value"] = original_benchmark_loader()
            benchmark_cache["loaded"] = True
        return benchmark_cache["value"]

    service.load_market_benchmark = cached_benchmark_loader

    all_results = []
    for trading_date in dates:
        rows = service.replay(
            trading_date=trading_date,
            min_money=args.min_money,
            checkpoints=checkpoints,
            limit=None,
        )
        rows = [HistoricalCandidateRankerService.rank([_normalize_spot_readiness(item) for item in rows], limit=args.limit)]
        rows = rows[0]
        for item in rows:
            item["_trading_date"] = trading_date
            item["confirmation_window"] = service.confirmation_window(
                item.get("futures_confirmation_time")
            )
            item["outcome_10_00"] = _forward_outcome(service, item, "10:00")
            item["outcome_13_00"] = _forward_outcome(service, item, "13:00")
        _print_rows(rows, trading_date)
        all_results.extend((trading_date, item) for item in rows)

    _save_replay_results(all_results, dates, args.min_money)

    if len(dates) > 1:
        available = [item for _, item in all_results if (item.get("outcome_13_00") or {}).get("available")]
        wins = [item for item in available if float((item.get("outcome_13_00") or {}).get("directional_return_percent", 0) or 0) > 0]
        avg_dir = sum(float((item.get("outcome_13_00") or {}).get("directional_return_percent", 0) or 0) for item in available) / len(available) if available else 0.0
        avg_mfe = sum(float((item.get("outcome_13_00") or {}).get("max_favorable_percent", 0) or 0) for item in available) / len(available) if available else 0.0
        print()
        print("=== MULTI-DATE QUICK SUMMARY ===")
        print(f"DATES: {len(dates)} | CANDIDATES: {len(all_results)} | OUTCOMES: {len(available)}")
        print(f"DIR WIN RATE: {len(wins) / len(available) * 100:.1f}%" if available else "DIR WIN RATE: N/A")
        print(f"AVG DIR %: {avg_dir:.2f} | AVG MFE %: {avg_mfe:.2f}")

        for window in ("EARLY", "LATE", "NONE"):
            window_items = [
                item for _, item in all_results
                if item.get("confirmation_window") == window
            ]

            window_outcomes = [
                item for item in window_items
                if (item.get("outcome_13_00") or {}).get("available")
            ]

            window_wins = [
                item for item in window_outcomes
                if float(
                    (item.get("outcome_13_00") or {}).get(
                        "directional_return_percent", 0
                    ) or 0
                ) > 0
            ]

            window_avg_dir = (
                sum(
                    float(
                        (item.get("outcome_13_00") or {}).get(
                            "directional_return_percent", 0
                        ) or 0
                    )
                    for item in window_outcomes
                ) / len(window_outcomes)
                if window_outcomes else 0.0
            )

            window_avg_mfe = (
                sum(
                    float(
                        (item.get("outcome_13_00") or {}).get(
                            "max_favorable_percent", 0
                        ) or 0
                    )
                    for item in window_outcomes
                ) / len(window_outcomes)
                if window_outcomes else 0.0
            )

            if window_outcomes:
                print(
                    f"{window}: CANDIDATES {len(window_items)} | "
                    f"OUTCOMES {len(window_outcomes)} | "
                    f"WIN RATE {len(window_wins) / len(window_outcomes) * 100:.1f}% | "
                    f"AVG DIR {window_avg_dir:.2f}% | "
                    f"AVG MFE {window_avg_mfe:.2f}%"
                )
            else:
                print(
                    f"{window}: CANDIDATES {len(window_items)} | "
                    f"OUTCOMES 0 | WIN RATE N/A"
                )

        print("Historical replay is read-only and does not perform portfolio or order operations.")
        print("Trade readiness is SPOT-first; futures confirmation is secondary outcome data only.")


if __name__ == "__main__":
    main()
