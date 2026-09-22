import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Program"))

from Cloud.market_data_engine import CloudMarketDataEngine


class FakeRadar:
    def __init__(self):
        self._last_scan_diagnostics = {"radar": "ok"}

    def scan(self, limit=10):
        return [{"ticker": "TEST", "selection_role": "MARKET_LEADER"}]


class FakeFutures:
    def __init__(self):
        self.api = object()

    def scan(self):
        return [{"ticker": "TESTF", "money_flow_status": "NO_DATA"}], {"futures": "ok"}


class FakeMoneyFlow:
    WINDOW_MINUTES = 30
    LIQUIDITY_WINDOW_MINUTES = 5

    def analyze(self, rows, api=None):
        return rows


def test_engine_publishes_shared_snapshot():
    engine = CloudMarketDataEngine(scan_interval_seconds=30, radar_limit=10)
    engine._radar = FakeRadar()
    engine._futures = FakeFutures()
    engine._money_flow = FakeMoneyFlow()

    snapshot = engine.scan_once()
    payload = snapshot.as_dict()

    assert snapshot.version == 1
    assert payload["data_policy"] == "REAL_BCS_DATA_ONLY"
    assert payload["radar"][0]["ticker"] == "TEST"
    assert payload["futures_oi"][0]["ticker"] == "TESTF"
    assert payload["timing"]["total_ms"] >= 0
    assert payload["timing"]["radar_ms"] >= 0
    assert payload["timing"]["futures_oi_ms"] >= 0
    assert payload["timing"]["money_flow_ms"] >= 0
    assert "radar_breakdown_seconds" in payload["timing"]
    assert engine.status["status"] == "READY"
    assert engine.status["timing"]["total_ms"] == payload["timing"]["total_ms"]


def test_subscriber_gets_current_snapshot():
    engine = CloudMarketDataEngine(scan_interval_seconds=30)
    engine._radar = FakeRadar()
    engine._futures = FakeFutures()
    engine._money_flow = FakeMoneyFlow()

    engine.scan_once()
    queue = engine.subscribe()
    payload = asyncio.run(queue.get())

    assert payload["version"] == 1
    assert "timing" in payload
    engine.unsubscribe(queue)
    assert engine.subscriber_count == 0
