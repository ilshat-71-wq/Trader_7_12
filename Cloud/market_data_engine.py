"""Shared Cloud Market Data Engine for Trader_7_12 Pro.

The engine runs the existing read-only market-information pipeline once and
serves the cached result to many desktop clients. It never creates synthetic
market data and it never executes trades.

Architecture:
    BCS/MOEX -> one cloud scanner -> immutable snapshot -> API/WebSocket clients

The cloud process owns the BCS read-only credential. Desktop clients do not
need direct BCS credentials when using this engine.
"""

from __future__ import annotations

import asyncio
import copy
import os
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from services.market_information_scanner_service import MarketInformationScannerService
from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
from services.money_flow_service import MoneyFlowService
from Cloud.morning_radar_service import MorningRadarService


ENGINE_VERSION = "1.1.0"
DEFAULT_SCAN_INTERVAL_SECONDS = 300
DEFAULT_RADAR_LIMIT = 20


def _json_safe(value: Any) -> Any:
    """Convert scanner output into JSON-safe primitive values."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, set):
        return sorted(_json_safe(v) for v in value)
    return value


@dataclass
class EngineSnapshot:
    version: int
    generated_at: str
    engine_version: str
    radar: list[dict[str, Any]]
    radar_diagnostics: dict[str, Any]
    futures_oi: list[dict[str, Any]]
    futures_diagnostics: dict[str, Any]
    timing: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return _json_safe({
            "version": self.version,
            "generated_at": self.generated_at,
            "engine_version": self.engine_version,
            "data_policy": "REAL_BCS_DATA_ONLY",
            "decision_policy": "NO_TRADE_EXECUTION",
            "radar": self.radar,
            "radar_diagnostics": self.radar_diagnostics,
            "futures_oi": self.futures_oi,
            "futures_diagnostics": self.futures_diagnostics,
            "timing": self.timing,
        })


class CloudMarketDataEngine:
    """Single-process shared scanner with cached snapshots and subscribers."""

    def __init__(
        self,
        *,
        scan_interval_seconds: int | None = None,
        radar_limit: int | None = None,
    ):
        self.scan_interval_seconds = max(
            30,
            int(
                scan_interval_seconds
                or os.getenv(
                    "CLOUD_SCAN_INTERVAL_SECONDS",
                    DEFAULT_SCAN_INTERVAL_SECONDS,
                )
            ),
        )
        self.radar_limit = max(
            1,
            int(radar_limit or os.getenv("CLOUD_RADAR_LIMIT", DEFAULT_RADAR_LIMIT)),
        )

        self._radar = MarketInformationScannerService()
        self._futures = FuturesOIMarketDataScannerService()
        self._money_flow = MoneyFlowService()
        self.morning_radar = MorningRadarService()

        self._scan_lock = threading.Lock()
        self._snapshot_lock = threading.RLock()
        self._snapshot: EngineSnapshot | None = None
        self._version = 0
        self._started_at = time.time()
        self._last_scan_started_at: float | None = None
        self._last_scan_finished_at: float | None = None
        self._last_scan_error: str | None = None
        self._last_scan_timing: dict[str, Any] = {}

        self._subscribers: set[asyncio.Queue] = set()
        self._subscriber_lock = threading.Lock()

    @property
    def snapshot(self) -> EngineSnapshot | None:
        with self._snapshot_lock:
            return copy.deepcopy(self._snapshot)

    @property
    def status(self) -> dict[str, Any]:
        with self._snapshot_lock:
            snapshot = self._snapshot
            return {
                "status": "READY" if snapshot else "STARTING",
                "engine_version": ENGINE_VERSION,
                "snapshot_version": snapshot.version if snapshot else 0,
                "generated_at": snapshot.generated_at if snapshot else None,
                "scan_interval_seconds": self.scan_interval_seconds,
                "radar_limit": self.radar_limit,
                "last_scan_error": self._last_scan_error,
                "last_scan_started_at": self._iso_timestamp(self._last_scan_started_at),
                "last_scan_finished_at": self._iso_timestamp(self._last_scan_finished_at),
                "uptime_seconds": round(time.time() - self._started_at, 1),
                "clients": self.subscriber_count,
                "data_policy": "REAL_BCS_DATA_ONLY",
                "decision_policy": "NO_TRADE_EXECUTION",
                "timing": self._last_scan_timing,
                "morning_radar": self.morning_radar.summary(),
            }

    @property
    def subscriber_count(self) -> int:
        with self._subscriber_lock:
            return len(self._subscribers)

    @staticmethod
    def _iso_timestamp(timestamp: float | None) -> str | None:
        if timestamp is None:
            return None
        return datetime.fromtimestamp(timestamp).astimezone().isoformat()

    @staticmethod
    def _timing_ms(start: float, end: float) -> float:
        return round((end - start) * 1000.0, 1)

    def scan_once(self) -> EngineSnapshot:
        """Run the production scanners exactly once and publish one snapshot."""
        if not self._scan_lock.acquire(blocking=False):
            existing = self.snapshot
            if existing is not None:
                return existing
            raise RuntimeError("A market scan is already running.")

        scan_started = time.perf_counter()
        self._last_scan_started_at = time.time()
        try:
            radar_started = time.perf_counter()
            radar_rows = self._radar.scan(limit=self.radar_limit)
            radar_finished = time.perf_counter()
            radar_diagnostics = dict(
                getattr(self._radar, "_last_scan_diagnostics", {}) or {}
            )

            futures_started = time.perf_counter()
            futures_rows, futures_diagnostics = self._futures.scan()
            futures_finished = time.perf_counter()

            money_flow_started = time.perf_counter()
            futures_rows = self._money_flow.analyze(
                futures_rows,
                api=self._futures.api,
            )
            money_flow_finished = time.perf_counter()

            available = [
                row for row in futures_rows
                if row.get("money_flow_status") == "AVAILABLE"
            ]
            hot = [
                row for row in available
                if row.get("money_flow_liquidity_state") == "HOT"
            ]
            futures_diagnostics = dict(futures_diagnostics or {})
            futures_diagnostics.update({
                "money_flow_status": "AVAILABLE" if available else "NO_DATA",
                "money_flow_available": len(available),
                "money_flow_hot_liquidity": len(hot),
                "money_flow_top_ranked": min(5, len(available)),
                "money_flow_window_minutes": MoneyFlowService.WINDOW_MINUTES,
                "money_flow_liquidity_window_minutes": MoneyFlowService.LIQUIDITY_WINDOW_MINUTES,
                "money_flow_source": "BCS_LAST_TRADES_30M_PLUS_CURRENT_ORDER_BOOK",
                "money_flow_policy": "REAL_BCS_DATA_ONLY; NO_PARTICIPANT_IDENTITY_CLAIM",
            })

            snapshot_started = time.perf_counter()
            with self._snapshot_lock:
                self._version += 1
                snapshot = EngineSnapshot(
                    version=self._version,
                    generated_at=datetime.now().astimezone().isoformat(),
                    engine_version=ENGINE_VERSION,
                    radar=_json_safe(radar_rows),
                    radar_diagnostics=_json_safe(radar_diagnostics),
                    futures_oi=_json_safe(futures_rows),
                    futures_diagnostics=_json_safe(futures_diagnostics),
                    timing={},
                )
                self._snapshot = snapshot
                self._last_scan_error = None
                self._last_scan_finished_at = time.time()
            snapshot_finished = time.perf_counter()

            total_finished = time.perf_counter()
            timing = {
                "radar_ms": self._timing_ms(radar_started, radar_finished),
                "futures_oi_ms": self._timing_ms(futures_started, futures_finished),
                "money_flow_ms": self._timing_ms(money_flow_started, money_flow_finished),
                "snapshot_ms": self._timing_ms(snapshot_started, snapshot_finished),
                "total_ms": self._timing_ms(scan_started, total_finished),
                "total_seconds": round(total_finished - scan_started, 3),
            }

            radar_timing = radar_diagnostics.get("timings_seconds", {})
            timing["radar_breakdown_seconds"] = {
                key: radar_timing[key]
                for key in (
                    "universe",
                    "benchmark",
                    "benchmark_d1",
                    "m5",
                    "d1",
                    "calculation",
                    "total",
                )
                if key in radar_timing
            }
            timing["universe_breakdown_seconds"] = dict(
                radar_timing.get("universe_breakdown", {}) or {}
            )
            timing["benchmark_breakdown_seconds"] = dict(
                radar_timing.get("benchmark_breakdown", {}) or {}
            )

            with self._snapshot_lock:
                snapshot.timing = timing
                self._last_scan_timing = dict(timing)

            print(
                "CLOUD SCAN TIMING:",
                f"RADAR={timing['radar_ms'] / 1000:.3f}s",
                f"FUTURES_OI={timing['futures_oi_ms'] / 1000:.3f}s",
                f"MONEY_FLOW={timing['money_flow_ms'] / 1000:.3f}s",
                f"SNAPSHOT={timing['snapshot_ms'] / 1000:.3f}s",
                f"TOTAL={timing['total_seconds']:.3f}s",
            )
            if timing["radar_breakdown_seconds"]:
                print(
                    "RADAR BREAKDOWN:",
                    " ".join(
                        f"{key.upper()}={value:.3f}s"
                        for key, value in timing["radar_breakdown_seconds"].items()
                    ),
                )
            if timing["universe_breakdown_seconds"]:
                print(
                    "UNIVERSE BREAKDOWN:",
                    " ".join(
                        f"{key.upper()}={value:.3f}s"
                        for key, value in timing["universe_breakdown_seconds"].items()
                        if isinstance(value, (int, float))
                    ),
                )
                spot_breakdown = timing["universe_breakdown_seconds"].get("spot_load_breakdown") or {}
                by_type = spot_breakdown.get("by_type") or {}
                if by_type:
                    print(
                        "SPOT METADATA BY TYPE:",
                        " ".join(
                            f"{kind}={details.get('seconds', 0):.3f}s/{details.get('records', 0)}"
                            for kind, details in by_type.items()
                            if isinstance(details, dict)
                        ),
                    )
            if timing["benchmark_breakdown_seconds"]:
                print(
                    "BENCHMARK BREAKDOWN:",
                    " ".join(
                        f"{key.upper()}={value:.3f}s"
                        for key, value in timing["benchmark_breakdown_seconds"].items()
                        if isinstance(value, (int, float))
                    ),
                )
                benchmark_requests = timing["benchmark_breakdown_seconds"].get("requests") or {}
                if benchmark_requests:
                    print(
                        "BENCHMARK REQUESTS:",
                        " ".join(
                            f"{ticker}="
                            f"{details.get('candles_seconds', 0):.3f}s"
                            f"/{details.get('candle_count', 0)}"
                            + (
                                f"+Q{details.get('quote_fallback_seconds', 0):.3f}s"
                                if "quote_fallback_seconds" in details else ""
                            )
                            for ticker, details in benchmark_requests.items()
                            if isinstance(details, dict)
                        ),
                    )

            self._publish(snapshot)
            return copy.deepcopy(snapshot)
        except Exception as exc:
            self._last_scan_error = f"{type(exc).__name__}: {exc}"
            self._last_scan_finished_at = time.time()
            raise
        finally:
            self._scan_lock.release()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        with self._subscriber_lock:
            self._subscribers.add(queue)
        snapshot = self.snapshot
        if snapshot is not None:
            try:
                queue.put_nowait(snapshot.as_dict())
            except asyncio.QueueFull:
                pass
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._subscriber_lock:
            self._subscribers.discard(queue)

    def _publish(self, snapshot: EngineSnapshot) -> None:
        payload = snapshot.as_dict()
        with self._subscriber_lock:
            subscribers = tuple(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

    async def run_forever(self) -> None:
        """Run regular refreshes plus exact Moscow Morning Radar slots."""
        last_regular_scan = 0.0
        last_slot_key = None
        while True:
            now = datetime.now(self.morning_radar.TIMEZONE)
            today = self.morning_radar.load(now.date().isoformat())
            captured_today = {
                str(item.get("slot"))
                for item in (today.get("snapshots") or [])
                if item.get("slot")
            }
            slot = None
            for candidate in self.morning_radar.SLOTS:
                candidate_dt = datetime.combine(now.date(), candidate, tzinfo=self.morning_radar.TIMEZONE)
                age_seconds = (now - candidate_dt).total_seconds()
                if 0 <= age_seconds <= 300 and candidate.strftime("%H:%M") not in captured_today:
                    slot = candidate.strftime("%H:%M")
                    break
            slot_key = f"{now.date().isoformat()}:{slot}" if slot else None

            if slot and slot_key != last_slot_key:
                try:
                    snapshot = await asyncio.to_thread(self.scan_once)
                    self.morning_radar.record(snapshot.as_dict(), slot=slot)
                except Exception:
                    # Leave the slot unmarked so the next 5-second poll retries it.
                    await asyncio.sleep(5.0)
                    continue
                last_slot_key = slot_key
                last_regular_scan = time.monotonic()
                await asyncio.sleep(5.0)
                continue

            elapsed = time.monotonic() - last_regular_scan
            if elapsed >= self.scan_interval_seconds:
                try:
                    await asyncio.to_thread(self.scan_once)
                except Exception:
                    pass
                last_regular_scan = time.monotonic()
                continue

            # Five-second polling is lightweight and guarantees the exact
            # 20-second Morning Radar slot window is observed.
            await asyncio.sleep(min(5.0, max(1.0, self.scan_interval_seconds - elapsed)))
