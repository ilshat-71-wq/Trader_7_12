from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from Cloud.morning_radar import MORNING_SLOTS, MorningRadarService


MSK = ZoneInfo("Europe/Moscow")


def _snapshot(regime="UP", ticker="ABC", recent=100.0, rpm=10.0, accel=0.0, rs=-0.5, change=-0.2):
    return {
        "radar": [{
            "spot_ticker": ticker,
            "change_percent": change,
            "relative_strength": rs,
            "money_per_minute": rpm,
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
        },
        "futures_oi": [],
        "futures_diagnostics": {},
        "timing": {},
    }


def test_schedule_is_exact_moscow_slots():
    service = MorningRadarService("/tmp/trader_test_morning_radar.json")
    assert service.due_slots() == (
        "07:00", "07:15", "07:30", "08:00", "09:00", "09:45", "09:50"
    )
    assert service.due_slot(datetime(2026, 9, 23, 7, 0, tzinfo=MSK)) == "07:00"
    assert service.due_slot(datetime(2026, 9, 23, 9, 50, tzinfo=MSK)) == "09:50"


def test_history_derives_interest_and_up_market_short_watch(tmp_path: Path):
    service = MorningRadarService(str(tmp_path / "morning.json"))
    t1 = datetime(2026, 9, 23, 7, 0, tzinfo=MSK)
    t2 = datetime(2026, 9, 23, 7, 15, tzinfo=MSK)
    first = service.record_if_due(_snapshot(), t1)
    assert first["stocks"][0]["interest"] == "BASE"
    assert first["stocks"][0]["short_watch"] is True

    second = service.record_if_due(
        _snapshot(recent=120.0, rpm=12.0, accel=30.0),
        t2,
    )
    assert second["stocks"][0]["interest"] == "↑"
    assert second["stocks"][0]["recent_money_delta_pct"] == 20.0
    assert second["stocks"][0]["short_watch_persistence"] == 2


def test_persistence_round_trip(tmp_path: Path):
    path = tmp_path / "morning.json"
    service = MorningRadarService(str(path))
    t = datetime(2026, 9, 23, 9, 50, tzinfo=MSK)
    service.record_if_due(_snapshot(), t)

    restored = MorningRadarService(str(path))
    payload = restored.as_dict(t.date())
    assert payload["complete"] is True
    assert payload["captured_slots"] == ["09:50"]
