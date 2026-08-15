from datetime import datetime
from zoneinfo import ZoneInfo

from services.morning_replay_service import MorningReplayService


class FakeHistoryService:
    def __init__(self, candles):
        self.candles = candles

    def to_moscow(self, value):
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text).astimezone(ZoneInfo("Europe/Moscow"))

    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5):
        return list(self.candles)


class FakeSetupEngine:
    MAX_LOOKBACK_CANDLES = 36

    def __init__(self):
        self.calls = []

    def analyze(self, candles, direction):
        self.calls.append((len(candles), direction))
        return {
            "setup": "RETEST",
            "setup_state": "READY",
            "entry_trigger": 101.0,
            "level": 100.0,
            "setup_index": max(0, len(candles) - 2),
            "confirmation_index": max(0, len(candles) - 1),
        }


def test_replay_uses_only_candles_available_by_checkpoint():
    candles = [
        {"time": "2026-08-14T04:00:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:05:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:10:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:15:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
    ]
    service = MorningReplayService(history_service=FakeHistoryService(candles))
    result = service.load_candles("YDEX", "SPBRU", "2026-08-14", "07:10")
    assert len(result) == 3


def test_replay_calls_setup_engine_with_checkpoint_candles():
    candles = [
        {"time": f"2026-08-14T04:{m:02d}:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1}
        for m in (0, 5, 10, 15, 20, 25)
    ]
    setup_engine = FakeSetupEngine()
    service = MorningReplayService(
        history_service=FakeHistoryService(candles),
        setup_engine=setup_engine,
    )
    results = service.replay_setup(
        "YDEX", "SPBRU", "LONG", "2026-08-14",
        checkpoints=["07:15", "07:30"],
    )
    assert len(results) == 2
    assert setup_engine.calls == [(4, "LONG"), (6, "LONG")]
    assert results[0]["setup"] == "RETEST"
    assert results[0]["setup_state"] == "READY"
    assert results[0]["entry_trigger"] == 101.0
    assert results[1]["candles"] == 6
