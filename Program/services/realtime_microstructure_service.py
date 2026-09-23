"""Real-time BCS market microstructure for Trader_7_12 Pro.

Read-only WebSocket layer:
- real Level-2 order book, up to 20 levels;
- real anonymized trades;
- no synthetic prices/volume;
- directional scores describe observed pressure, not probability or participant identity.
"""

from collections import defaultdict, deque
from datetime import datetime, timezone
import json
import threading
import time

from PySide6.QtCore import QObject, Signal

try:
    import websocket
except ImportError:  # pragma: no cover - environment dependent
    websocket = None


class RealtimeMicrostructureWorker(QObject):
    snapshot = Signal(object)
    status = Signal(object)
    failed = Signal(str)
    finished = Signal()

    WS_URL = "wss://ws.broker.ru/trade-api-market-data-connector/api/v1/market-data/ws"
    DEPTH = 20
    MAX_INSTRUMENTS = 100
    TRADE_WINDOW_SECONDS = 60
    EMIT_MIN_INTERVAL_SECONDS = 0.15
    RECONNECT_SECONDS = 2.0

    def __init__(self, api, instruments):
        super().__init__()
        self.api = api
        self.instruments = [
            {
                "ticker": str(item.get("ticker") or "").upper(),
                "classCode": str(item.get("classCode") or "").upper(),
            }
            for item in (instruments or [])
            if item.get("ticker") and item.get("classCode")
        ][: self.MAX_INSTRUMENTS]
        self._stop_event = threading.Event()
        self._books = {}
        self._trades = defaultdict(deque)
        self._last_emit = {}
        self._connected_at = None
        self._ws = None
        self._ws_lock = threading.Lock()

    def stop(self):
        self._stop_event.set()
        # Interrupt blocking recv() so Qt can shut the worker down cleanly.
        with self._ws_lock:
            ws = self._ws
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    @staticmethod
    def _float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    @classmethod
    def _score_from_delta(cls, delta_pct):
        return round(max(0.0, min(100.0, 50.0 + float(delta_pct) * 0.5)), 1)

    def _book_metrics(self, payload):
        bids = payload.get("bids") or []
        asks = payload.get("asks") or []
        bid_qty = self._float(payload.get("bidVolume"))
        ask_qty = self._float(payload.get("askVolume"))
        if not bid_qty:
            bid_qty = sum(self._float(x.get("quantity")) for x in bids if isinstance(x, dict))
        if not ask_qty:
            ask_qty = sum(self._float(x.get("quantity")) for x in asks if isinstance(x, dict))
        total = bid_qty + ask_qty
        imbalance_pct = ((bid_qty - ask_qty) / total * 100.0) if total else 0.0

        best_bid = self._float(bids[0].get("price")) if bids and isinstance(bids[0], dict) else 0.0
        best_ask = self._float(asks[0].get("price")) if asks and isinstance(asks[0], dict) else 0.0
        spread_pct = ((best_ask / best_bid - 1.0) * 100.0) if best_bid > 0 and best_ask > 0 else None
        bid_money = sum(
            self._float(x.get("price")) * self._float(x.get("quantity"))
            for x in bids if isinstance(x, dict)
        )
        ask_money = sum(
            self._float(x.get("price")) * self._float(x.get("quantity"))
            for x in asks if isinstance(x, dict)
        )
        return {
            "book_bid_qty": round(bid_qty, 4),
            "book_ask_qty": round(ask_qty, 4),
            "book_bid_money": round(bid_money, 2),
            "book_ask_money": round(ask_money, 2),
            "book_imbalance_pct": round(imbalance_pct, 2),
            "book_score": self._score_from_delta(imbalance_pct),
            "book_spread_pct": round(spread_pct, 5) if spread_pct is not None else None,
            "book_levels": max(len(bids), len(asks)),
        }

    def _tape_metrics(self, ticker):
        now = time.time()
        queue = self._trades[ticker]
        while queue and now - queue[0][0] > self.TRADE_WINDOW_SECONDS:
            queue.popleft()
        if not queue:
            return {
                "tape_score": None,
                "tape_delta_pct": None,
                "tape_buy_money": 0.0,
                "tape_sell_money": 0.0,
                "tape_trade_count": 0,
                "tape_money_per_minute": 0.0,
                "tape_acceleration_pct": None,
            }

        buy = sum(v for _, side, v, _ in queue if side == "BUY")
        sell = sum(v for _, side, v, _ in queue if side == "SELL")
        total = buy + sell
        delta_pct = (buy - sell) / total * 100.0 if total else 0.0

        half_cut = now - self.TRADE_WINDOW_SECONDS / 2
        old = [v for ts, _, v, _ in queue if ts < half_cut]
        recent = [v for ts, _, v, _ in queue if ts >= half_cut]
        old_rate = sum(old) / (self.TRADE_WINDOW_SECONDS / 2) if old else 0.0
        recent_rate = sum(recent) / (self.TRADE_WINDOW_SECONDS / 2) if recent else 0.0
        acceleration = ((recent_rate / old_rate) - 1.0) * 100.0 if old_rate > 0 else None

        return {
            "tape_score": self._score_from_delta(delta_pct),
            "tape_delta_pct": round(delta_pct, 2),
            "tape_buy_money": round(buy, 2),
            "tape_sell_money": round(sell, 2),
            "tape_trade_count": len(queue),
            "tape_money_per_minute": round(total, 2),
            "tape_acceleration_pct": round(acceleration, 2) if acceleration is not None else None,
        }

    def _emit_snapshot(self, ticker, class_code):
        now = time.time()
        if now - self._last_emit.get(ticker, 0.0) < self.EMIT_MIN_INTERVAL_SECONDS:
            return
        self._last_emit[ticker] = now

        book = self._books.get(ticker)
        if not book:
            return
        book_metrics = self._book_metrics(book)
        tape_metrics = self._tape_metrics(ticker)
        components = [x for x in (book_metrics.get("book_score"), tape_metrics.get("tape_score")) if x is not None]
        flow_score = round(sum(components) / len(components), 1) if components else None
        if flow_score is None:
            state = "NO_DATA"
        elif flow_score >= 70:
            state = "BUY_PRESSURE"
        elif flow_score <= 30:
            state = "SELL_PRESSURE"
        else:
            state = "BALANCED"

        payload = {
            "ticker": ticker,
            "classCode": class_code,
            "realtime_status": "LIVE",
            "realtime_source": "BCS_WEBSOCKET_MARKET_DATA",
            "observed_at": self._now().isoformat(),
            **book_metrics,
            **tape_metrics,
            "flow_score": flow_score,
            "flow_state": state,
        }
        self.snapshot.emit(payload)

    def _handle(self, payload):
        if not isinstance(payload, dict):
            return
        response_type = str(payload.get("responseType") or "")
        ticker = str(payload.get("ticker") or "").upper()
        if not ticker:
            return
        class_code = str(payload.get("classCode") or "").upper()

        if response_type == "OrderBook":
            self._books[ticker] = payload
            self._emit_snapshot(ticker, class_code)
            return

        if response_type == "LastTrades":
            side = str(payload.get("side") or "").upper()
            if side not in {"BUY", "SELL"}:
                return
            price = self._float(payload.get("price"))
            quantity = self._float(payload.get("quantity"))
            value = price * quantity if price > 0 and quantity > 0 else self._float(payload.get("volume"))
            if value <= 0:
                return
            self._trades[ticker].append((time.time(), side, value, payload.get("dateTime")))
            self._emit_snapshot(ticker, class_code)

    def _subscribe(self, ws):
        if not self.instruments:
            return
        for data_type in (0, 2):
            message = {
                "subscribeType": 0,
                "dataType": data_type,
                "instruments": self.instruments,
            }
            if data_type == 0:
                message["depth"] = self.DEPTH
            ws.send(json.dumps(message))

    def run(self):
        if not self.instruments:
            self.status.emit({"state": "NO_INSTRUMENTS"})
            self.finished.emit()
            return
        if websocket is None:
            self.failed.emit(
                "BCS realtime dependency is missing: install websocket-client."
            )
            self.finished.emit()
            return
        try:
            if not self.api.authorize():
                self.failed.emit("BCS realtime authorization failed.")
                self.finished.emit()
                return
            token = self.api.access_token
            while not self._stop_event.is_set():
                ws = None
                try:
                    ws = websocket.create_connection(
                        self.WS_URL,
                        header=[f"Authorization: Bearer {token}"],
                        timeout=10,
                        enable_multithread=True,
                    )
                    ws.settimeout(1.0)
                    with self._ws_lock:
                        self._ws = ws
                    self._connected_at = self._now()
                    self.status.emit({
                        "state": "LIVE",
                        "source": "BCS_WEBSOCKET_MARKET_DATA",
                        "instruments": len(self.instruments),
                        "connected_at": self._connected_at.isoformat(),
                    })
                    self._subscribe(ws)
                    while not self._stop_event.is_set():
                        try:
                            raw = ws.recv()
                            if raw is None:
                                raise RuntimeError("BCS WebSocket closed")
                            if isinstance(raw, bytes):
                                raw = raw.decode("utf-8", errors="replace")
                            self._handle(json.loads(raw))
                        except Exception as exc:
                            if self._stop_event.is_set():
                                break
                            if websocket is not None and isinstance(exc, websocket.WebSocketTimeoutException):
                                continue
                            raise
                except Exception as exc:
                    if not self._stop_event.is_set():
                        self.status.emit({
                            "state": "RECONNECTING",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                        time.sleep(self.RECONNECT_SECONDS)
                finally:
                    with self._ws_lock:
                        if self._ws is ws:
                            self._ws = None
                    if ws is not None:
                        try:
                            ws.close()
                        except Exception:
                            pass
        finally:
            self.status.emit({"state": "STOPPED"})
            self.finished.emit()
