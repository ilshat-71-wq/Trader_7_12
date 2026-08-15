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


class FakeRadarService:
    SETUP_LOOKBACK_CANDLES = 36

    @staticmethod
    def _empty_setup(direction="NONE"):
        return {
            "setup": "NONE",
            "setup_direction": direction,
            "setup_state": "WAIT",
            "entry_trigger": 0.0,
            "previous_high": 0.0,
            "previous_low": 0.0,
        }

    @staticmethod
    def _detect_long_setup(candles):
        return {
            "setup": "FIRST_PULLBACK",
            "setup_direction": "LONG",
            "setup_state": "WAIT",
            "entry_trigger": 0.0,
            "previous_high": 101.0,
            "previous_low": 99.0,
        }

    @staticmethod
    def _detect_short_setup(candles):
        return {
            "setup": "FIRST_REBOUND",
            "setup_direction": "SHORT",
            "setup_state": "READY",
            "entry_trigger": 98.0,
            "previous_high": 100.0,
            "previous_low": 98.0,
        }


def test_replay_uses_only_candles_available_by_checkpoint():
    candles = [
        {"time": "2026-08-14T04:00:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:05:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:10:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:15:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
    ]

    service = MorningReplayService(
        history_service=FakeHistoryService(candles),
        radar_service=FakeRadarService(),
    )

    result = service.load_candles(
        "YDEX",
        "SPBRU",
        "2026-08-14",
        "07:10",
    )

    assert len(result) == 3


def test_replay_returns_setup_state_at_each_checkpoint():
    candles = [
        {"time": "2026-08-14T04:00:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:05:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:10:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
        {"time": "2026-08-14T04:15:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1},
    ]

    service = MorningReplayService(
        history_service=FakeHistoryService(candles),
        radar_service=FakeRadarService(),
    )

    results = service.replay_setup(
        "YDEX",
        "SPBRU",
        "SHORT",
        "2026-08-14",
        checkpoints=["07:15", "07:30"],
    )

    assert len(results) == 2
    assert results[0]["setup"] == "FIRST_REBOUND"
    assert results[0]["setup_state"] == "READY"
    assert results[0]["entry_trigger"] == 98.0
