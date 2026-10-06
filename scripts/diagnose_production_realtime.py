#!/usr/bin/env python3
"""Qt-correct production realtime diagnostic for Trader_7_12 Pro."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from collections import Counter
from PySide6.QtCore import QCoreApplication, QObject, QThread, QTimer, Slot

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "Program"
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.realtime_microstructure_service import RealtimeMicrostructureWorker


class TracedRealtimeWorker(RealtimeMicrostructureWorker):
    """Exact production worker with counters only."""
    def __init__(self, api, instruments):
        super().__init__(api, instruments)
        self.emit_attempts = 0
        self.emit_tickers = Counter()
        self.book_tickers = Counter()
        self.tape_tickers = Counter()

    def _handle(self, payload):
        if isinstance(payload, dict):
            ticker = str(payload.get("ticker") or "").upper()
            response_type = str(payload.get("responseType") or "")
            if response_type == "OrderBook" and ticker:
                self.book_tickers[ticker] += 1
            elif response_type == "LastTrades" and ticker:
                self.tape_tickers[ticker] += 1
        super()._handle(payload)

    def _emit_snapshot(self, ticker, class_code):
        self.emit_attempts += 1
        super()._emit_snapshot(ticker, class_code)
        if ticker in self._last_emit:
            self.emit_tickers[ticker] += 1


class Collector(QObject):
    def __init__(self, worker, thread, seconds):
        super().__init__()
        self.worker = worker
        self.thread = thread
        self.seconds = float(seconds)
        self.snapshots = []
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.finish)

    @Slot(object)
    def on_status(self, status):
        s = dict(status or {})
        state = s.get("state", "—")
        if state in {"CONNECTED","SUBSCRIBED","SUBSCRIPTION_ERROR",
                     "SUBSCRIPTION_TIMEOUT","LIVE","RECONNECTING","STOPPED"}:
            print(
                f"STATUS            {state}"
                f" | BOOK {s.get('orderbook_accepted',0)}/{s.get('orderbook_requested',0)}"
                f" | TAPE {s.get('lasttrades_accepted',0)}/{s.get('lasttrades_requested',0)}"
                f" | MSG {s.get('orderbook_messages',0)}/{s.get('lasttrades_messages',0)}"
            )

    @Slot(object)
    def on_snapshot(self, item):
        item = dict(item or {})
        self.snapshots.append(item)
        print(
            f"SNAPSHOT          {str(item.get('ticker') or '—').upper()}"
            f" | BOOK {item.get('book_score')}"
            f" | TAPE {item.get('tape_score')}"
            f" | FLOW {item.get('flow_score')}"
        )

    def start(self):
        self.thread.start()
        self.timer.start(max(1000, int(self.seconds * 1000)))

    def finish(self):
        self.worker.stop()
        QTimer.singleShot(6000, self.hard_finish)

    def hard_finish(self):
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
        QCoreApplication.instance().quit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seconds", type=float, default=20.0)
    p.add_argument("--ticker", type=str, default=None,
                   help="Optional exact futures ticker to isolate, e.g. SIZ6")
    args = p.parse_args()

    print("=== BCS PRODUCTION REALTIME / QT DIAGNOSTIC ===")
    print("Diagnostic only: production Radar/Futures logic is not modified.")
    print("Same QThread + Qt event-loop model as the application.")
    print(f"Observation window: {args.seconds:.1f}s\n")

    print("=== STAGE 1 / PRODUCTION INSTRUMENT SET ===")
    service = FuturesOIMarketDataScannerService()
    try:
        results, diagnostics = service.scan()
    except Exception as exc:
        print(f"SCAN              FAIL: {type(exc).__name__}: {exc}")
        return 2

    print(f"SCAN STATUS       {(diagnostics or {}).get('status','—')}")
    print(f"CONTRACTS         {len(results or [])}")

    instruments, seen = [], set()
    for item in results or []:
        ticker = str(item.get("futures_ticker") or "").upper()
        code = str(item.get("futures_class_code") or "SPBFUT").upper()
        if ticker and code and (ticker, code) not in seen:
            instruments.append({"ticker": ticker, "classCode": code})
            seen.add((ticker, code))

    if args.ticker:
        target = args.ticker.strip().upper()
        instruments = [x for x in instruments if x["ticker"] == target]
        if not instruments:
            print(f"INSTRUMENT SET     FAIL: ticker {target} not found")
            return 3
        print(f"TARGET            {target} / {instruments[0]["classCode"]}")

    if not instruments:
        print("INSTRUMENT SET     FAIL")
        return 3
    for x in instruments:
        print(f"  {x['ticker']:10s} / {x['classCode']}")
    print(f"SUBSCRIPTIONS      {len(instruments)}\n")

    print("=== STAGE 2 / REAL PRODUCTION QTHREAD PATH ===")
    app = QCoreApplication(sys.argv)
    thread = QThread()
    worker = TracedRealtimeWorker(service.api, instruments)
    worker.moveToThread(thread)
    collector = Collector(worker, thread, args.seconds)

    worker.status.connect(collector.on_status)
    worker.snapshot.connect(collector.on_snapshot)
    worker.finished.connect(thread.quit)
    thread.started.connect(worker.run)
    thread.finished.connect(worker.deleteLater)

    collector.start()
    app.exec()

    print("\n=== STAGE 3 / RAW RESULT ===")
    accepted_book = sorted(worker._subscription_accepted[0])
    accepted_tape = sorted(worker._subscription_accepted[2])
    expected = sorted((x["ticker"], x["classCode"]) for x in instruments)

    print(f"BOOK ACK           {len(accepted_book)}/{len(expected)}")
    print(f"TAPE ACK           {len(accepted_tape)}/{len(expected)}")
    print(f"BOOK MESSAGE       {worker._message_counts['OrderBook']}")
    print(f"TAPE MESSAGE       {worker._message_counts['LastTrades']}")
    if args.ticker:
        target = args.ticker.strip().upper()
        target_book = worker.book_tickers.get(target, 0)
        target_tape = worker.tape_tickers.get(target, 0)
        target_snapshot = sum(1 for item in collector.snapshots if str(item.get("ticker") or "").upper() == target)
        print(f"{target} BOOK MESSAGE  {"YES" if target_book else "NO"}")
        print(f"{target} BOOK COUNT    {target_book}")
        print(f"{target} TAPE MESSAGE  {"YES" if target_tape else "NO"}")
        print(f"{target} TAPE COUNT    {target_tape}")
        print(f"{target} SNAPSHOTS     {target_snapshot}")
    print(f"LIVE DATA SEEN     {worker._live_data_seen}")
    print(f"SNAPSHOT EMITS     {worker.emit_attempts}")
    print(f"SNAPSHOT RECEIVED  {len(collector.snapshots)}")
    print(f"LAST MESSAGE       {worker._last_message_at or '—'}")
    print(f"LAST ERROR         {worker._last_error or 'NONE'}")
    print(f"SUB ERRORS         {worker._subscription_errors or 'NONE'}")

    missing_book = sorted(set(expected) - set(accepted_book))
    missing_tape = sorted(set(expected) - set(accepted_tape))
    if missing_book:
        print("BOOK ACK MISSING    " + ", ".join(f"{t}/{c}" for t,c in missing_book))
    if missing_tape:
        print("TAPE ACK MISSING    " + ", ".join(f"{t}/{c}" for t,c in missing_tape))

    received = sorted({str(x.get("ticker") or "").upper()
                       for x in collector.snapshots if x.get("ticker")})
    print("SNAPSHOT TICKERS    " + (", ".join(received) if received else "—"))

    print("\n=== DIAGNOSTIC VERDICT ===")
    if missing_book or missing_tape:
        print("RESULT             SUBSCRIPTION ACK MISMATCH")
        return 10
    if worker._message_counts["OrderBook"] == 0 and worker._message_counts["LastTrades"] == 0:
        print("RESULT             NO REALTIME MARKET-DATA MESSAGES")
        return 11
    if args.ticker:
        target = args.ticker.strip().upper()
        if target_book:
            print(f"RESULT             {target} BOOK MESSAGE: YES")
        else:
            print(f"RESULT             {target} BOOK MESSAGE: NO")

    if worker.emit_attempts > 0 and not collector.snapshots:
        print("RESULT             SNAPSHOT EMIT EXISTS BUT QT RECEIVER GETS NOTHING")
        print("NEXT               Qt signal/thread handoff")
        return 12
    if collector.snapshots:
        print("RESULT             PRODUCTION QT REALTIME PATH DELIVERS SNAPSHOTS")
        print("NEXT               compare UI _realtime_snapshot/table update")
        return 0
    print("RESULT             RAW DATA RECEIVED BUT SNAPSHOT EMIT NOT REACHED")
    print("NEXT               worker parse/emit path")
    return 13


if __name__ == "__main__":
    raise SystemExit(main())
