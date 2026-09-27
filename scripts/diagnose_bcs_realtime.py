#!/usr/bin/env python3
"""Diagnostic-only BCS WebSocket probe.

Uses the existing local BCSAPI refresh-token configuration and the documented
market-data WebSocket protocol. It does not modify Radar, OI, or realtime
production code and never prints credentials.

The probe deliberately uses the documented real MOEX instrument SBER/TQBR.
The metadata lookup is not used as a gate because it may return an empty
collection outside the trading session; that must not prevent testing the
WebSocket path itself.

Run from the repository root:
    python3 scripts/diagnose_bcs_realtime.py
"""

from __future__ import annotations

import json
import ssl
import sys
import time
from collections import Counter
from pathlib import Path

import certifi

try:
    import websocket
except ImportError:
    print("DEPENDENCY FAIL: websocket-client is not installed")
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "Program"
if str(PROGRAM) not in sys.path:
    sys.path.insert(0, str(PROGRAM))

from api.bcs_api import BCSAPI  # noqa: E402


WS_URL = "wss://ws.broker.ru/trade-api-market-data-connector/api/v1/market-data/ws"
DEPTH = 20
PROBE_SECONDS = 20
TICKER = "SBER"
CLASS_CODE = "TQBR"


def short_type(payload: object) -> str:
    if not isinstance(payload, dict):
        return type(payload).__name__
    return str(payload.get("responseType") or payload.get("type") or "NO_RESPONSE_TYPE")


def main() -> int:
    print("=== BCS REALTIME DIAGNOSTIC PROBE ===")
    print("Diagnostic only: production realtime code is not modified.")
    print("Instrument: canonical real BCS/MOEX SBER / TQBR")
    print()

    api = BCSAPI()
    print("AUTH              ...")
    if not api.authorize():
        print("AUTH              FAIL")
        return 1
    print("AUTH              OK")
    print(f"INSTRUMENT         {TICKER} / {CLASS_CODE}")
    print()

    token = api.access_token
    if not token:
        print("AUTH TOKEN         FAIL: no access token")
        return 1

    response_types = Counter()
    errors = []
    book_ack = False
    tape_ack = False
    book_messages = 0
    tape_messages = 0
    last_book = None
    last_tape = None
    ws_connected = False

    print("WS CONNECT        ...")
    ws = None
    try:
        ws = websocket.create_connection(
            WS_URL,
            header=[f"Authorization: Bearer {token}"],
            timeout=10,
            enable_multithread=True,
            sslopt={
                "cert_reqs": ssl.CERT_REQUIRED,
                "ca_certs": certifi.where(),
            },
        )
        ws_connected = True
        ws.settimeout(1.0)
        print("WS CONNECT        OK")

        book_request = {
            "subscribeType": 0,
            "dataType": 0,
            "depth": DEPTH,
            "instruments": [{"ticker": TICKER, "classCode": CLASS_CODE}],
        }
        tape_request = {
            "subscribeType": 0,
            "dataType": 2,
            "instruments": [{"ticker": TICKER, "classCode": CLASS_CODE}],
        }

        ws.send(json.dumps(book_request))
        print("BOOK SUBMIT       OK")

        ws.send(json.dumps(tape_request))
        print("TAPE SUBMIT       OK")

        deadline = time.monotonic() + PROBE_SECONDS
        while time.monotonic() < deadline:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue

            if raw is None:
                errors.append("WebSocket closed by server")
                break
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                response_types["INVALID_JSON"] += 1
                print("RAW INVALID_JSON")
                continue

            rt = short_type(payload)
            response_types[rt] += 1

            if rt == "OrderBookSuccess":
                book_ack = True
                print("BOOK ACK          OK")
            elif rt == "LastTradesSuccess":
                tape_ack = True
                print("TAPE ACK          OK")
            elif rt == "OrderBook":
                book_messages += 1
                last_book = payload.get("dateTime")
            elif rt == "LastTrades":
                tape_messages += 1
                last_tape = payload.get("dateTime")
            elif rt == "Error" or payload.get("errors"):
                raw_errors = payload.get("errors") or payload.get("error") or []
                if isinstance(raw_errors, dict):
                    raw_errors = [raw_errors]
                if not isinstance(raw_errors, list):
                    raw_errors = [raw_errors]
                for error in raw_errors:
                    if isinstance(error, dict):
                        code = error.get("code") or error.get("errorCode") or "UNKNOWN"
                        message = error.get("message") or error.get("description") or str(error)
                        errors.append(f"{code}: {message}")
                    else:
                        errors.append(str(error))

    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        if not ws_connected:
            print(f"WS CONNECT        FAIL: {type(exc).__name__}: {exc}")
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    print()
    print("=== RESULT ===")
    print("AUTH              OK")
    print(f"WS CONNECT        {'OK' if ws_connected else 'FAIL'}")
    print("BOOK SUBMIT       OK" if ws_connected else "BOOK SUBMIT       NOT SENT")
    print("TAPE SUBMIT       OK" if ws_connected else "TAPE SUBMIT       NOT SENT")
    print(f"BOOK ACK          {'OK' if book_ack else 'FAIL'}")
    print(f"BOOK MESSAGE      {book_messages}")
    print(f"LAST BOOK         {last_book or '—'}")
    print(f"TAPE ACK          {'OK' if tape_ack else 'FAIL'}")
    print(f"TAPE MESSAGE      {tape_messages}")
    print(f"LAST TAPE         {last_tape or '—'}")
    print(f"RAW RESPONSE TYPES {dict(response_types)}")
    print(f"ERROR             {errors[-10:] if errors else 'NONE'}")
    print("RECONNECT         NO (diagnostic probe is single-connection)")
    print()
    print("=== INTERPRETATION ===")
    if book_ack and book_messages and tape_ack and tape_messages:
        print("WS DATA PATH      BOOK + TAPE REAL DATA RECEIVED")
    elif book_ack or tape_ack:
        print("WS DATA PATH      PARTIAL: at least one subscription acknowledged")
    elif errors:
        print("WS DATA PATH      NO ACK; inspect BCS error(s) above")
    else:
        print("WS DATA PATH      CONNECTED BUT NO ACK/DATA DURING PROBE WINDOW")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
