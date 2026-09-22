import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Program"))

from Cloud.market_data_engine import CloudMarketDataEngine


class FakeRadar:
    def __init__(self):
        self._last_scan_diagnostics = {
            "radar": "ok",
            "timings_seconds": {
                "universe": 1.0,
                "benchmark": 2.0,
                "benchmark_d1": 0.1,
                "m5": 0.2,
                "d1": 0.3,
                "calculation": 0.4,
                "total": 4.0,
                "universe_breakdown": {
                    "spot_load": 3.0,
                    "macro_metadata": 0.5,
                    "filtering": 0.1,
                    "assembly": 0.1,
                    "total": 3.7,
                    "spot_records": 9321,
                    "macro_records": 4,
                    "universe_records": 263,
                },
                "benchmark_breakdown": {
                    "metadata": 1.0,
                    "indices_fallback": 0.0,
                    "candles": 1.0,
                    "quote_fallback": 0.0,
                    "total": 2.0,
                    "metadata_records": 2,
                    "indices_fallback_records": 0,
                    "resolved_benchmarks": ["IMOEX2", "IRUS2"],
                },
            },
        }

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
    assert payload["timing"]["universe_breakdown_seconds"]["spot_load"] == 3.0
    assert payload["timing"]["benchmark_breakdown_seconds"]["candles"] == 1.0
    assert engine.status["timing"]["universe_breakdown_seconds"]["spot_records"] == 9321
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
