"""Read-only diagnostic for the dynamic BCS Futures -> SPOT universe pipeline."""

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from api.bcs_api import BCSAPI
from services.futures_universe_service import FuturesUniverseService
from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.historical_universe_replay_service import HistoricalUniverseReplayService
from services.stage1_mapping_diagnostic import Stage1MappingDiagnostic

DEFAULT_DATE = "2026-08-14"
DEFAULT_MIN_MONEY = 100_000_000.0


def as_date(value):
    return date.fromisoformat(str(value)[:10])


def load_spot_inventory(api, spot_types):
    inventory = {}
    records_by_key = {}

    for instrument_type in spot_types:
        try:
            records = api.get_instruments(instrument_type)
        except Exception:
            records = []

        records = records if isinstance(records, list) else []
        inventory[instrument_type] = len(records)

        for record in records:
            if not isinstance(record, dict):
                continue

            ticker = str(record.get("ticker") or "").strip().upper()
            if not ticker:
                continue

            boards = record.get("boards") or []
            class_code = ""
            if isinstance(boards, list):
                for board in boards:
                    if isinstance(board, dict) and board.get("classCode"):
                        class_code = str(board["classCode"]).strip()
                        break

            class_code = class_code or str(record.get("classCode") or "").strip()
            if class_code:
                records_by_key[(ticker, class_code)] = record

    return inventory, records_by_key


def historical_money(history_service, ticker, class_code, trading_date, days=5):
    trading_date = as_date(trading_date)
    end_moscow = datetime.combine(
        trading_date,
        datetime.min.time(),
    ).replace(tzinfo=history_service.MOSCOW_TZ)
    start_utc = end_moscow.astimezone(timezone.utc) - timedelta(days=12)
    end_utc = end_moscow.astimezone(timezone.utc)

    try:
        data = history_service.trade_service.api.get_candles(
            ticker,
            class_code,
            interval="D",
            start_time=start_utc,
            end_time=end_utc,
        )
    except Exception:
        return [], 0.0

    bars = data.get("bars", []) if isinstance(data, dict) else []
    completed = []

    for bar in bars:
        if not isinstance(bar, dict):
            continue

        candle_date = history_service.get_moscow_date(bar.get("time"))
        if candle_date is None or candle_date >= trading_date:
            continue

        try:
            close = float(bar.get("close") or 0)
            volume = float(bar.get("volume") or 0)
        except (TypeError, ValueError):
            continue

        if close > 0:
            completed.append((candle_date, close, volume))

    completed.sort(key=lambda item: item[0])
    selected = completed[-days:]
    # BCS candles-chart already returns daily volume as money turnover.
    # Do not multiply by close again.
    turnovers = [
        volume
        for _, close, volume in selected
        if close > 0 and volume > 0
    ]
    average = sum(turnovers) / len(turnovers) if turnovers else 0.0
    return completed, average


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose the dynamic Futures -> SPOT universe."
    )
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--min-money", type=float, default=DEFAULT_MIN_MONEY)
    args = parser.parse_args()

    api = BCSAPI()
    if not api.authorize():
        raise SystemExit("BCS authorization failed")

    print("=" * 100)
    print("TRADER_7_12 PRO - DYNAMIC UNIVERSE PIPELINE DIAGNOSTIC")
    print("READ ONLY — NO ORDERS")
    print(
        f"HISTORICAL DATE: {args.date} | "
        f"MIN AVG DAILY MONEY: {args.min_money:,.0f}"
    )
    print("=" * 100)

    futures_raw = api.get_instruments("FUTURES")
    futures_raw = futures_raw if isinstance(futures_raw, list) else []

    futures_service = FuturesUniverseService(api)
    futures_normalized = futures_service.load(authorize=False)

    mapping_service = FuturesSpotMappingService(
        api=api,
        futures_universe_service=futures_service,
    )
    spot_types = mapping_service.SPOT_INSTRUMENT_TYPES
    spot_inventory, spot_records = load_spot_inventory(api, spot_types)
    spots = list(spot_records.values())

    print("STAGE 1 — INSTRUMENT INVENTORY")
    print(f"ALL FUTURES FROM BCS        : {len(futures_raw)}")
    print(f"ELIGIBLE DATED FUTURES      : {len(futures_normalized)}")
    for instrument_type in spot_types:
        print(f"SPOT {instrument_type:<20}: {spot_inventory.get(instrument_type, 0)}")
    print(f"UNIQUE SPOT RECORDS         : {len(spots)}")
    print()

    diagnostic = Stage1MappingDiagnostic(mapping_service)
    analysis = diagnostic.analyze(futures_normalized, spots)
    mappings = analysis["mapped_rows"]

    print("STAGE 2 — FUTURES -> SPOT MAPPING")
    print(f"FUTURES ENTERING MAPPING   : {analysis['futures']}")
    print(f"SUCCESSFULLY MAPPED        : {analysis['mapped']}")
    print(f"UNMAPPED / AMBIGUOUS       : {analysis['unmapped']}")
    print()
    print("MAPPING FAILURE REASONS")
    for reason, count in sorted(
        analysis["failure_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    ):
        print(f"  {reason:<35} {count}")

    failures = analysis["failures"]
    if failures:
        print()
        print("UNMAPPED SAMPLE — FIRST 20")
        for item in failures[:20]:
            ticker = str(item.get("futures_ticker") or "-")
            reason = str(item.get("reason") or "-")
            print(f"  {ticker:<12} {reason}")
    print()

    history_service = HistoricalUniverseReplayService().history_service
    history_ok = 0
    history_missing = 0
    liquid = 0
    samples = []
    history_by_spot = {}

    for mapping in mappings:
        spot = str(mapping.get("spot_ticker") or "").strip().upper()
        class_code = str(mapping.get("spot_class_code") or "").strip()

        if not spot or not class_code:
            history_missing += 1
            continue

        # Do not request the same SPOT history once per futures contract.
        cache_key = (spot, class_code)
        if cache_key not in history_by_spot:
            history_by_spot[cache_key] = historical_money(
                history_service,
                spot,
                class_code,
                args.date,
            )

        candles, average_money = history_by_spot[cache_key]
        if candles:
            history_ok += 1
        else:
            history_missing += 1

        if average_money >= args.min_money:
            liquid += 1
            if len(samples) < 10:
                samples.append(
                    (
                        mapping.get("futures_ticker"),
                        spot,
                        average_money,
                        len(candles),
                    )
                )

    print("STAGE 3 — SPOT HISTORY")
    print(f"MAPPED FUTURES/SPOTS        : {len(mappings)}")
    print(f"SPOTS WITH DAILY HISTORY    : {history_ok}")
    print(f"SPOTS WITHOUT HISTORY       : {history_missing}")
    print(f"UNIQUE SPOT HISTORY REQUESTS: {len(history_by_spot)}")
    print()

    print("STAGE 4 — HISTORICAL LIQUIDITY")
    print(f"LIQUID AVG MONEY >= LIMIT  : {liquid}")
    print()
    print("LIQUID SAMPLE")
    for futures_ticker, spot, average_money, candles in samples:
        print(
            f"  {str(futures_ticker or '-'):10} -> {spot:10} "
            f"AVG={average_money:,.0f} DAYS={candles}"
        )
    print("=" * 100)


if __name__ == "__main__":
    main()
