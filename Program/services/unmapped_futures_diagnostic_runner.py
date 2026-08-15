"""Read-only deep diagnostic for Futures -> SPOT mapping failures."""

import argparse
from collections import Counter, defaultdict

from api.bcs_api import BCSAPI
from services.futures_universe_service import FuturesUniverseService
from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.stage1_mapping_diagnostic import Stage1MappingDiagnostic

DEFAULT_DATE = "2026-08-14"


def load_spots(api, mapping_service):
    records = []
    seen = set()
    for instrument_type in mapping_service.SPOT_INSTRUMENT_TYPES:
        try:
            rows = api.get_instruments(instrument_type)
        except Exception:
            rows = []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            class_code = mapping_service._class_code(row)
            if not ticker or not class_code:
                continue
            key = (ticker, class_code)
            if key not in seen:
                seen.add(key)
                records.append(row)
    return records


def classify(failure):
    metadata = failure.get("metadata") or {}
    explicit_ticker = str(
        metadata.get("baseAssetSecuritySecCode")
        or metadata.get("underlyingTicker")
        or metadata.get("underlyingSecurityCode")
        or metadata.get("underlyingAssetTicker")
        or metadata.get("spotTicker")
        or ""
    ).strip().upper()
    explicit_class = str(
        metadata.get("baseAssetSecurityClassCode")
        or metadata.get("underlyingSecurityClassCode")
        or ""
    ).strip()
    base_asset = metadata.get("baseAsset")
    base_security = metadata.get("baseAssetSecurity")
    return explicit_ticker, explicit_class, base_asset, base_security


def main():
    parser = argparse.ArgumentParser(description="Deeply inspect unmapped dynamic futures")
    parser.add_argument("--date", default=DEFAULT_DATE)
    args = parser.parse_args()

    api = BCSAPI()
    if not api.authorize():
        raise SystemExit("BCS authorization failed")

    futures_service = FuturesUniverseService(api)
    futures = futures_service.load(authorize=False)
    mapping_service = FuturesSpotMappingService(api=api, futures_universe_service=futures_service)
    spots = load_spots(api, mapping_service)
    analysis = Stage1MappingDiagnostic(mapping_service).analyze(futures, spots)
    failures = [item for item in analysis["failures"] if item.get("reason") == "EXPLICIT_UNDERLYING_NOT_IN_SPOT"]

    spot_index = mapping_service._build_spot_index(spots)
    class_counts = Counter()
    underlying_counts = Counter()
    missing_underlying_counts = Counter()
    rows = []

    for failure in failures:
        ticker = str(failure.get("futures_ticker") or "-")
        explicit_ticker, explicit_class, base_asset, base_security = classify(failure)
        class_counts[explicit_class or "<NO_CLASS>"] += 1
        underlying_counts[explicit_ticker or "<NO_TICKER>"] += 1
        candidates = spot_index.get(explicit_ticker, []) if explicit_ticker else []
        if not candidates:
            missing_underlying_counts[explicit_ticker or "<NO_TICKER>"] += 1
        rows.append((ticker, explicit_ticker, explicit_class, base_asset, base_security, len(candidates)))

    rows.sort(key=lambda row: (row[1], row[0]))

    print("=" * 120)
    print("TRADER_7_12 PRO - UNMAPPED FUTURES DEEP DIAGNOSTIC")
    print("READ ONLY — NO ORDERS")
    print(f"DATE: {args.date}")
    print("=" * 120)
    print(f"ELIGIBLE FUTURES                 : {len(futures)}")
    print(f"TOTAL SPOT RECORDS               : {len(spots)}")
    print(f"EXPLICIT UNDERLYING NOT IN SPOT  : {len(failures)}")
    print()

    print("UNDERLYING CLASS DISTRIBUTION")
    for key, count in class_counts.most_common():
        print(f"  {key:<35} {count}")
    print()

    print("UNIQUE MISSING UNDERLYINGS")
    print(f"  UNIQUE TICKERS: {len(underlying_counts)}")
    for ticker, count in underlying_counts.most_common():
        print(f"  {ticker:<20} {count}")
    print()

    print("DETAILED CONTRACTS")
    print("FUTURES       UNDERLYING           CLASS       CANDIDATES  BASE_ASSET")
    print("-" * 120)
    for ticker, underlying, class_code, base_asset, base_security, candidates in rows:
        print(
            f"{ticker:<13} {underlying or '-':<20} "
            f"{class_code or '-':<11} {candidates:<11} "
            f"{str(base_asset or base_security or '-')}"
        )
    print("=" * 120)


if __name__ == "__main__":
    main()
