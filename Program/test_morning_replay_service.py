from datetime import datetime
from zoneinfo import ZoneInfo

from services.morning_replay_service import MorningReplayService


class FakeHistoryService:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    def __init__(self, candles): self.candles = candles
    def to_moscow(self, value): return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(self.MOSCOW_TZ)
    def load(self, ticker, class_code, start_time=None, end_time=None, timeframe_minutes=5): return list(self.candles)


def test_replay_uses_only_candles_available_by_checkpoint():
    candles = [{"time": f"2026-08-14T04:{m:02d}:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1} for m in (0, 5, 10, 15)]
    service = MorningReplayService(history_service=FakeHistoryService(candles))
    result = service.load_candles("YDEX", "SPBRU", "2026-08-14", "07:10")
    assert len(result) == 3


def test_replay_uses_canonical_spot_setup_engine():
    candles = [{"time": f"2026-08-14T04:{m:02d}:00.000Z", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1} for m in (0, 5, 10, 15, 20, 25)]
    service = MorningReplayService(history_service=FakeHistoryService(candles))
    results = service.replay_setup("YDEX", "SPBRU", "LONG", "2026-08-14", checkpoints=["07:15", "07:30"])
    assert len(results) == 2
    assert [x["candles"] for x in results] == [4, 6]
    assert all(x["direction"] == "LONG" for x in results)
    assert all(x["setup_state"] in {"WAIT", "WATCH", "READY", "CONFIRMED"} for x in results)
    assert all("entry_trigger" in x for x in results)
    assert all(x["momentum_signal"] == "NO_SIGNAL" for x in results)
