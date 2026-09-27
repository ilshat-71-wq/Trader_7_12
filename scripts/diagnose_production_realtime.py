#!/usr/bin/env python3
"""Production-path diagnostic for BCS realtime Futures OI.

Diagnostic only. It uses the same Futures OI scanner and the same
RealtimeMicrostructureWorker as the production app, but never changes
Radar/Futures algorithms and never prints credentials.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "Program"
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

from services.futures_oi_marketdata_scanner_service import (  # noqa: E402
    FuturesOIMarketDataScannerService,
)
from services.realtime_microstructure_service import (  # noqa: E402
    RealtimeMicrostructureWorker,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="BCS production realtime diagnostic")
    parser.add_argument("--seconds", type=float, default=20.0)
    args = parser.parse_args()

    print("=== BCS PRODUCTION REALTIME DIAGNOSTIC ===")
    print("Diagnostic only: no Radar/Futures logic is modified.")
    print(f"Observation window: {args.seconds:.1f}s")
    print()

    # Stage 1: use the exact production Futures OI scanner to obtain the
    # instruments that production _start_realtime() receives.
    print("=== STAGE 1 / PRODUCTION INSTRUMENT SET ===")
    service = FuturesOIMarketDataScannerService()
    try:
        results, diagnostics = service.scan()
    except Exception as exc:
        print(f"SCAN              FAIL: {type(exc).__name__}: {exc}")
        return 2

    diagnostics = diagnostics or {}
    print(f"SCAN STATUS       {diagnostics.get('status', '—')}")
    print(f"CONTRACTS         {len(results)}")

    instruments = []
    seen = set()
    for item in results or []:
        ticker = str(item.get("futures_ticker") or "").upper()
        class_code = str(item.get("futures_class_code") or "SPBFUT").upper()
        if ticker and class_code and (ticker, class_code) not in seen:
            instruments.append({"ticker": ticker, "classCode": class_code})
            seen.add((ticker, class_code))

    if not instruments:
        print("INSTRUMENT SET     FAIL: production scan returned no realtime futures")
        return 3

    for item in instruments:
        print(f"  {item['ticker']:10s} / {item['classCode']}")

    print(f"SUBSCRIPTIONS      {len(instruments)}")
    print()

    # Stage 2: use the exact production realtime worker.
    print("=== STAGE 2 / PRODUCTION REALTIME WORKER ===")
    api = service.api
    worker = RealtimeMicrostructureWorker(api, instruments)
    statuses = []
    snapshots = []

    def on_status(status):
        status = dict(status or {})
        statuses.append(status)
        state = status.get("state", "—")
        if state in {
            "CONNECTED",
            "SUBSCRIBED",
            "SUBSCRIPTION_ERROR",
            "SUBSCRIPTION_TIMEOUT",
            "LIVE",
            "RECONNECTING",
        }:
            print(
                f"STATUS            {state}"
                f" | BOOK {status.get('orderbook_accepted', 0)}/{status.get('orderbook_requested', 0)}"
                f" | TAPE {status.get('lasttrades_accepted', 0)}/{status.get('lasttrades_requested', 0)}"
                f" | MSG {status.get('orderbook_messages', 0)}/{status.get('lasttrades_messages', 0)}"
            )

    def on_snapshot(item):
        item = dict(item or {})
        snapshots.append(item)

    worker.status.connect(on_status)
    worker.snapshot.connect(on_snapshot)

    thread = threading.Thread(target=worker.run, name="bcs-production-realtime-diagnostic", daemon=True)
    started = time.monotonic()
    thread.start()
    thread.join(timeout=max(1.0, args.seconds))
    if thread.is_alive():
        worker.stop()
        thread.join(timeout=5.0)

    elapsed = time.monotonic() - started
    print()
    print("=== STAGE 3 / RAW RESULT ===")

    accepted_book = sorted(worker._subscription_accepted[0])
    accepted_tape = sorted(worker._subscription_accepted[2])
    expected = sorted((x["ticker"], x["classCode"]) for x in instruments)

    print(f"ELAPSED            {elapsed:.1f}s")
    print(f"BOOK ACK           {len(accepted_book)}/{len(expected)}")
    print(f"TAPE ACK           {len(accepted_tape)}/{len(expected)}")
    print(f"BOOK MESSAGE       {worker._message_counts['OrderBook']}")
    print(f"TAPE MESSAGE       {worker._message_counts['LastTrades']}")
    print(f"SNAPSHOTS          {len(snapshots)}")
    print(f"LIVE DATA SEEN     {worker._live_data_seen}")
    print(f"LAST MESSAGE       {worker._last_message_at or '—'}")
    print(f"LAST ERROR         {worker._last_error or 'NONE'}")
    print(f"SUB ERRORS         {worker._subscription_errors or 'NONE'}")

    missing_book = sorted(set(expected) - set(accepted_book))
    missing_tape = sorted(set(expected) - set(accepted_tape))
    if missing_book:
        print("BOOK ACK MISSING    " + ", ".join(f"{t}/{c}" for t, c in missing_book))
    if missing_tape:
        print("TAPE ACK MISSING    " + ", ".join(f"{t}/{c}" for t, c in missing_tape))

    snapshot_tickers = sorted({str(x.get("ticker") or "").upper() for x in snapshots if x.get("ticker")})
    if snapshot_tickers:
        print("SNAPSHOT TICKERS    " + ", ".join(snapshot_tickers))

    print()
    print("=== DIAGNOSTIC VERDICT ===")
    if worker._last_error and not worker._live_data_seen:
        print("RESULT             REALTIME WORKER ERROR / NO LIVE DATA")
        print("NEXT               inspect the exact error and ACK mismatch above")
        return 10

    if missing_book or missing_tape:
        print("RESULT             SUBSCRIPTION PARTIAL / ACK MISMATCH")
        print("NEXT               production instrument/classCode mapping")
        return 11

    if worker._message_counts["OrderBook"] == 0 and worker._message_counts["LastTrades"] == 0:
        print("RESULT             WS CONNECTED BUT NO MARKET-DATA MESSAGES")
        print("NEXT               production subscription/data delivery path")
        return 12

    if worker._message_counts["OrderBook"] > 0 and not snapshots:
        print("RESULT             RAW BOOK DATA RECEIVED BUT NO SNAPSHOTS")
        print("NEXT               production worker parse/emit path")
        return 13

    if snapshots:
        print("RESULT             PRODUCTION REALTIME WORKER IS RECEIVING LIVE DATA")
        print("NEXT               UI handoff / table update path")
        return 0

    print("RESULT             INCONCLUSIVE")
    return 14


if __name__ == "__main__":
    raise SystemExit(main())
