from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from Cloud.morning_radar_service import MorningRadarService


MSK = ZoneInfo("Europe/Moscow")


def _snapshot(regime="UP", ticker="ABC", recent=100.0, rpm=10.0, accel=0.0, rs=-0.5, change=-0.2):
    return {
        "generated_at": "2026-09-23T07:00:10+03:00",
        "radar": [{
            "spot_ticker": ticker,
            "change_percent": change,
            "relative_strength": rs,
            "money_per_minute": rpm,
            "recent_money_per_minute": recent / 15.0,
            "recent_money": recent,
            "money_acceleration": accel,
            "directional_score": 70,
            "signal": "LONG",
            "signal_probability": 70,
        }],
        "radar_diagnostics": {
            "market_regime": regime,
            "benchmark": "IMOEX2",
            "benchmark_change_percent": 1.2,
            "coverage_percent": 97.0,
            "countertrend_watch": [{
                "spot_ticker": ticker,
                "change_percent": change,
                "relative_strength": rs,
                "money_per_minute": rpm,
                "recent_money_per_minute": recent / 15.0,
                "recent_money": recent,
                "money_acceleration": accel,
                "directional_score": 70,
                "signal": "LONG",
                "signal_probability": 70,
            }],
        },
        "futures_oi": [],
        "futures_diagnostics": {},
        "timing": {},
    }


def test_schedule_is_exact_moscow_slots():
    service = MorningRadarService("/tmp/trader_test_morning_radar")
    assert [x for x in service.SLOTS] == [
        datetime.strptime(x, "%H:%M").time()
        for x in ("07:00", "07:15", "07:30", "08:00", "08:30", "08:45")
    ]
    assert service.slot_for(datetime(2026, 9, 23, 7, 0, 10, tzinfo=MSK)) == "07:00"
    assert service.slot_for(datetime(2026, 9, 23, 8, 45, 10, tzinfo=MSK)) == "08:45"
    assert service.slot_for(datetime(2026, 9, 23, 8, 50, 10, tzinfo=MSK)) is None


def test_history_derives_interest_and_countertrend_persistence(tmp_path: Path):
    service = MorningRadarService(str(tmp_path / "morning_radar"))
    t1 = datetime(2026, 9, 23, 7, 0, 10, tzinfo=MSK)
    t2 = datetime(2026, 9, 23, 7, 15, 10, tzinfo=MSK)

    first = service.record(_snapshot(), slot="07:00")
    assert first["snapshots"][0]["countertrend_watch"][0]["interest"]["state"] == "NEW"

    second_snapshot = _snapshot(recent=120.0, rpm=12.0, accel=30.0)
    second_snapshot["generated_at"] = t2.isoformat()
    second = service.record(second_snapshot, slot="07:15")
    summary = service.summary("2026-09-23")
    assert summary["short_watch_count"] == 1
    assert summary["latest"]["countertrend_watch"][0]["short_watch_persistence"] == 2
    assert summary["latest"]["countertrend_watch"][0]["interest"]["state"] == "RISING"


def test_persistence_round_trip(tmp_path: Path):
    path = tmp_path / "morning_radar"
    service = MorningRadarService(str(path))
    service.record(_snapshot(), slot="08:45")
    restored = MorningRadarService(str(path))
    payload = restored.summary("2026-09-23")
    assert payload["completed_slots"] == ["08:45"]
    assert payload["morning_complete"] is True
    assert payload["entry_handoff_time"] == "09:00"
    assert payload["snapshot_count"] == 1
