"""CLI runner for dynamic historical SPOT-first replay."""

import argparse
import json
from pathlib import Path

from services.historical_candidate_ranker_service import HistoricalCandidateRankerService
from services.historical_universe_replay_service import HistoricalUniverseReplayService


DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000
DEFAULT_CHECKPOINTS = "07:15,07:30,08:00,08:30,09:00,09:30,10:00,10:30,11:00,12:00,13:00"


def _normalize_spot_readiness(item):
    ready_time = item.get("ready_time")
    state = str(item.get("setup_state") or "WAIT").upper()
    trigger = float(item.get("entry_trigger", 0) or 0)
    item["spot_ready_time"] = ready_time
    item["spot_setup_state"] = state
    item["spot_entry_trigger"] = trigger
    item["trade_ready_time"] = ready_time
    item["readiness_source"] = "SPOT"
    item["readiness_confirmed_by_futures"] = False
    item["futures_confirmation_time"] = item.get("confirmation_time")
    item["futures_confirmation_status"] = "NO_DATA"
    return item


def _confirm_and_measure(service, item, endpoint):
    ticker = str(item.get("futures_ticker") or "").strip().upper()
    class_code = str(item.get("futures_class_code") or "").strip()
    direction = str(item.get("direction") or "").upper()
    confirmation_time = item.get("futures_confirmation_time")
    entry_price = float(item.get("futures_price", 0) or 0)
    if not ticker or not class_code or not confirmation_time or entry_price <= 0 or direction not in {"LONG", "SHORT"}:
        return {"available": False}
    confirmation = service.confirm_futures_at_checkpoint(ticker, class_code, direction, item.get("_trading_date"), confirmation_time)
    item["futures_confirmation"] = confirmation
    item["futures_confirmation_status"] = str(confirmation.get("status") or "NO_DATA").upper()
    item["readiness_confirmed_by_futures"] = item["futures_confirmation_status"] == "OK"
    candles = service.load_futures_candles(ticker, class_code, item.get("_trading_date"), endpoint)
    start = str(confirmation_time)[:8]
    candles = [c for c in candles if str(c.get("time") or "")[11:19] >= start]
    if not candles:
        return {"available": False}
    last_price = float(candles[-1].get("close", 0) or 0)
    if last_price <= 0:
        return {"available": False}
    sign = 1.0 if direction == "LONG" else -1.0
    raw_return = (last_price - entry_price) / entry_price * 100.0
    favorable, adverse = [], []
    for candle in candles:
        high, low = float(candle.get("high", 0) or 0), float(candle.get("low", 0) or 0)
        if direction == "LONG":
            if high > 0: favorable.append((high - entry_price) / entry_price * 100.0)
            if low > 0: adverse.append((low - entry_price) / entry_price * 100.0)
        else:
            if low > 0: favorable.append((entry_price - low) / entry_price * 100.0)
            if high > 0: adverse.append((entry_price - high) / entry_price * 100.0)
    return {"available": True, "endpoint": endpoint, "last_price": round(last_price, 4), "raw_return_percent": round(raw_return, 2), "directional_return_percent": round(raw_return * sign, 2), "max_favorable_percent": round(max(favorable), 2) if favorable else 0.0, "max_adverse_percent": round(min(adverse), 2) if adverse else 0.0}


def _save_replay_results(all_results, dates, min_money):
    output_dir = Path("Docs/historical_replay")
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"version": 3, "readiness_model": "SPOT_FIRST", "ranking_model": "SPOT_FIRST_BEFORE_FUTURES_MAPPING", "dates": list(dates), "min_money": float(min_money), "results": [{"trading_date": d, "item": item} for d, item in all_results]}
    output_path = output_dir / "latest_results.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved replay results: {output_path}")
    print(f"Saved records: {len(all_results)}")


def _print_rows(rows, trading_date):
    print()
    print("=" * 180)
    print("TRADER_7_12 PRO — HISTORICAL SPOT-FIRST TOP CANDIDATES")
    print(f"DATE: {trading_date} | READ ONLY")
    print("=" * 180)
    print(f"{'#':>3} {'SPOT':<8} {'DIR':<6} {'SCORE':>7} {'SETUP':<14} {'READY':<6} {'RS':>7} {'SPOT MONEY':>15} {'FUTURES':<10} {'FUT CONF':<9} {'10 DIR%':>9} {'13 DIR%':>9}")
    print("-" * 180)
    for rank, item in enumerate(rows, start=1):
        out10, out13 = item.get("outcome_10_00") or {}, item.get("outcome_13_00") or {}
        print(f"{rank:>3} {str(item.get('spot_ticker','-')):<8} {str(item.get('direction','-')):<6} {float(item.get('candidate_score',0) or 0):>7.2f} {str(item.get('setup','-')):<14} {str(item.get('trade_ready_time','-')):<6} {float(item.get('relative_strength',0) or 0):>7.2f} {float(item.get('average_daily_money',0) or 0):>15,.0f} {str(item.get('futures_ticker','-')):<10} {str(item.get('futures_confirmation_status','NO_DATA')):<9} {float(out10.get('directional_return_percent',0) or 0):>9.2f} {float(out13.get('directional_return_percent',0) or 0):>9.2f}")
    print("=" * 180)


def main():
    parser = argparse.ArgumentParser(description="Replay the canonical SPOT-first historical morning pipeline.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--dates", default=None)
    parser.add_argument("--min-money", type=float, default=DEFAULT_MIN_MONEY)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--checkpoints", default=DEFAULT_CHECKPOINTS)
    args = parser.parse_args()
    if args.date and args.dates:
        parser.error("use either --date or --dates, not both")
    dates = [x.strip() for x in (args.dates or args.date or DEFAULT_DATE).split(",") if x.strip()]
    checkpoints = [x.strip() for x in args.checkpoints.split(",") if x.strip()]

    service = HistoricalUniverseReplayService()
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
        rows = service.replay(trading_date=trading_date, min_money=args.min_money, checkpoints=checkpoints, limit=None)
        normalized = [_normalize_spot_readiness(item) for item in rows]
        ranked = HistoricalCandidateRankerService.rank(normalized, limit=args.limit)
        # Critical parity boundary: only the already-ranked SPOT shortlist gets futures context.
        ranked = service.attach_futures_context(ranked, trading_date)
        for item in ranked:
            item["_trading_date"] = trading_date
            if item.get("futures_ticker") and item.get("futures_confirmation_time"):
                item["outcome_10_00"] = _confirm_and_measure(service, item, "10:00")
                item["outcome_13_00"] = _confirm_and_measure(service, item, "13:00")
            else:
                item["outcome_10_00"] = {"available": False}
                item["outcome_13_00"] = {"available": False}
        _print_rows(ranked, trading_date)
        all_results.extend((trading_date, item) for item in ranked)

    _save_replay_results(all_results, dates, args.min_money)
    if len(dates) > 1:
        available = [item for _, item in all_results if (item.get("outcome_13_00") or {}).get("available")]
        wins = [item for item in available if float((item.get("outcome_13_00") or {}).get("directional_return_percent", 0) or 0) > 0]
        avg_dir = sum(float((item.get("outcome_13_00") or {}).get("directional_return_percent", 0) or 0) for item in available) / len(available) if available else 0.0
        avg_mfe = sum(float((item.get("outcome_13_00") or {}).get("max_favorable_percent", 0) or 0) for item in available) / len(available) if available else 0.0
        print(f"MULTI-DATE: DATES {len(dates)} | CANDIDATES {len(all_results)} | OUTCOMES {len(available)} | WIN RATE {len(wins)/len(available)*100:.1f}% | AVG DIR {avg_dir:.2f}% | AVG MFE {avg_mfe:.2f}%" if available else f"MULTI-DATE: DATES {len(dates)} | CANDIDATES {len(all_results)} | OUTCOMES 0 | WIN RATE N/A")
        print("Historical replay is read-only. SPOT ranking is completed before any futures mapping or confirmation lookup.")


if __name__ == "__main__":
    main()
