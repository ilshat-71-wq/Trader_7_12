from services.final_radar_service import FinalRadarService


def spot(ticker="VGSB", prob=91.0, used=25.0, accel=900.0, change=1.8):
    return {
        "spot_ticker": ticker,
        "signal": "LONG",
        "signal_probability": prob,
        "atr_used_percent": used,
        "atr_percent": 3.4,
        "money_acceleration": accel,
        "change_percent": change,
        "move_phase": "START",
        "directional_acceleration": accel,
    }


def test_requires_three_consecutive_scans_and_realtime():
    service = FinalRadarService()
    service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80, "flow_score": 75})
    service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []
    service.record_spot_scan([spot()], "2026-09-25")
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["spot_ticker"] == "VGSB"


def test_missing_realtime_does_not_promote():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []


def test_conflicting_futures_blocks_final():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot()], "2026-09-25")
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80, "flow_score": 75})
    service.update_futures([{
        "underlying_ticker": "VGSB",
        "futures_ticker": "VGSBZ6",
        "signal": "SHORT",
        "signal_probability": 80,
    }])
    assert service.final_candidates() == []


def test_day_change_resets_confirmation():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot()], "2026-09-25")
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80})
    assert service.final_candidates()
    service.record_spot_scan([spot()], "2026-09-26")
    assert service.final_candidates() == []
