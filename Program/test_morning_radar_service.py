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
        for x in ("07:00", "07:15", "07:30", "08:00", "09:00", "09:45", "09:50")
    ]
    assert service.slot_for(datetime(2026, 9, 23, 7, 0, 10, tzinfo=MSK)) == "07:00"
    assert service.slot_for(datetime(2026, 9, 23, 9, 50, 10, tzinfo=MSK)) == "09:50"


def test_slot_window_matches_scheduler_capture_window():
    service = MorningRadarService("/tmp/trader_test_morning_radar_window")
    assert service.slot_for(datetime(2026, 9, 23, 7, 0, 10, tzinfo=MSK)) == "07:00"
    assert service.slot_for(datetime(2026, 9, 23, 7, 4, 59, tzinfo=MSK)) == "07:00"
    assert service.slot_for(datetime(2026, 9, 23, 7, 5, 0, tzinfo=MSK)) == "07:00"
    assert service.slot_for(datetime(2026, 9, 23, 7, 5, 1, tzinfo=MSK)) is None


def test_0900_handoff_builds_real_futures_shortlist(tmp_path: Path):
    service = MorningRadarService(str(tmp_path / "morning_radar"))
    first = _snapshot()
    first["generated_at"] = "2026-09-23T07:00:10+03:00"
    first["futures_oi"] = [{
        "futures_ticker": "SIZ6",
        "change_percent": 1.2,
        "oi_analysis": {"oi_change_percent": 3.0},
        "money_flow_delta_pct": 20.0,
        "money_flow_liquidity_score": 80.0,
        "money_flow_position_action": "LONG_BUILDUP",
        "money_flow_signal": "ACCUMULATION",
    }]
    service.record(first, slot="07:00")

    second = dict(first)
    second["generated_at"] = "2026-09-23T09:00:10+03:00"
    second["futures_oi"] = [dict(first["futures_oi"][0])]
    summary = service.record(second, slot="09:00")
    handoff = service.summary("2026-09-23")["handoff"]

    assert handoff["status"] == "READY"
    assert handoff["captured"] is True
    assert handoff["slot"] == "09:00"
    assert handoff["rows"][0]["futures_ticker"] == "SIZ6"
    assert handoff["rows"][0]["morning_handoff"] is True
    assert handoff["rows"][0]["signal"] == "LONG"
    assert handoff["rows"][0]["signal_probability"] >= 55.0


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
    service.record(_snapshot(), slot="09:50")
    restored = MorningRadarService(str(path))
    payload = restored.summary("2026-09-23")
    assert payload["completed_slots"] == ["09:50"]
    assert payload["snapshot_count"] == 1
