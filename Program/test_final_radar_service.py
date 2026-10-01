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
        "liquidity_gate": True,
    }


def test_requires_three_consecutive_scans_and_realtime():
    service = FinalRadarService()
    service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []
    service.update_futures([future(underlying="VGSB")])
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80, "flow_score": 75})
    service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []
    service.record_spot_scan([spot()], "2026-09-25")
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["spot_ticker"] == "VGSB"


def test_illiquid_candidate_never_promotes():
    service = FinalRadarService()
    for _ in range(3):
        row = spot("PRMB")
        row["liquidity_gate"] = False
        service.record_spot_scan([row], "2026-09-25")
    service.update_realtime({"ticker": "PRMB", "book_score": 90, "tape_score": 90, "flow_score": 90})
    assert service.final_candidates() == []


def test_missing_realtime_does_not_promote():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot()], "2026-09-25")
    assert service.final_candidates() == []


def test_conflicting_futures_are_context_and_do_not_block_spot_final():
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
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["final_instrument_type"] == "SPOT"
    assert rows[0]["final_futures"]["state"] == "CONFLICT"


def test_day_change_resets_confirmation():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot()], "2026-09-25")
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80})
    service.update_futures([future(underlying="VGSB")])
    assert service.final_candidates()
    service.record_spot_scan([spot()], "2026-09-26")
    service.update_futures([future(underlying="VGSB")])
    assert service.final_candidates() == []


def future(contract="NGV6", prob=91.0, direction="LONG", underlying="NG"):
    return {
        "futures_ticker": contract,
        "oi_root": "NG",
        "underlying_ticker": underlying,
        "signal": direction,
        "signal_probability": prob,
        "turnover_rub": 11_000_000_000,
        "money_flow_status": "AVAILABLE",
        "money_flow_liquidity_state": "HOT",
        "money_flow_position_action": "LONG_BUILDUP" if direction == "LONG" else "SHORT_BUILDUP",
    }


def test_liquid_futures_can_promote_to_final():
    service = FinalRadarService()
    for _ in range(3):
        service.record_futures_scan([future()], "2026-09-25")
    service.update_realtime({
        "ticker": "NGV6",
        "book_score": 70,
        "tape_score": 80,
        "flow_score": 75,
    })
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["final_instrument_type"] == "FUTURES"
    assert rows[0]["futures_ticker"] == "NGV6"

def test_futures_final_exposes_own_futures_confirmation():
    service = FinalRadarService()
    for _ in range(3):
        service.record_futures_scan([future(contract="NGV6", prob=88.3)], "2026-09-25")
    service.update_realtime({
        "ticker": "NGV6",
        "book_score": 56,
        "tape_score": 100,
        "flow_score": 78,
    })
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["final_realtime"]["average"] == 78.0
    assert rows[0]["final_futures"]["state"] == "CONFIRMED"
    assert rows[0]["final_futures"]["contract"] == "NGV6"
    assert rows[0]["final_futures"]["probability"] == 88.3


def test_illiquid_futures_never_promote():
    service = FinalRadarService()
    row = future("PRMBF")
    row["turnover_rub"] = 0
    row["money_flow_liquidity_state"] = "NO_DATA"
    row["money_flow_status"] = "NO_DATA"
    for _ in range(3):
        service.record_futures_scan([row], "2026-09-25")
    service.update_realtime({
        "ticker": "PRMBF",
        "book_score": 90,
        "tape_score": 90,
        "flow_score": 90,
    })
    assert service.final_candidates() == []


def test_short_candidate_uses_negative_directional_acceleration():
    service = FinalRadarService()
    row = spot("EELT", prob=88.8, used=23.0, accel=-88.5, change=-1.30)
    row["signal"] = "SHORT"
    for _ in range(3):
        service.record_spot_scan([row], "2026-09-25")
    service.update_futures([future(contract="EELTZ6", direction="SHORT", underlying="EELT")])
    service.update_realtime({
        "ticker": "EELT",
        "book_score": 70,
        "tape_score": 80,
        "flow_score": 75,
    })
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["spot_ticker"] == "EELT"
    assert rows[0]["signal"] == "SHORT"


def test_short_candidate_with_positive_acceleration_is_rejected():
    service = FinalRadarService()
    row = spot("EELT", prob=88.8, used=23.0, accel=88.5, change=-1.30)
    row["signal"] = "SHORT"
    for _ in range(3):
        service.record_spot_scan([row], "2026-09-25")
    service.update_realtime({
        "ticker": "EELT",
        "book_score": 70,
        "tape_score": 80,
        "flow_score": 75,
    })
    assert service.final_candidates() == []


def test_missing_futures_match_does_not_block_spot_final():
    service = FinalRadarService()
    for _ in range(3):
        service.record_spot_scan([spot("VGSB")], "2026-09-25")
    service.update_realtime({"ticker": "VGSB", "book_score": 70, "tape_score": 80, "flow_score": 75})
    rows = service.final_candidates()
    assert len(rows) == 1
    assert rows[0]["final_futures"]["state"] == "NO_MATCH"


def test_final_contains_multiple_spot_and_futures_candidates_without_ranking():
    service = FinalRadarService()
    spot_a = spot("AAA1", prob=95.0, accel=800.0)
    spot_b = spot("BBB1", prob=82.0, accel=300.0)
    fut_a = future("NGV6", prob=88.0, underlying="NG")
    fut_b = future("ONZ6", prob=86.0, underlying="ON")
    for _ in range(3):
        service.record_spot_scan([spot_a, spot_b], "2026-09-25")
        service.record_futures_scan([fut_a, fut_b], "2026-09-25")
    for ticker in ("AAA1", "BBB1", "NGV6", "ONZ6"):
        service.update_realtime({
            "ticker": ticker,
            "book_score": 70,
            "tape_score": 80,
            "flow_score": 75,
        })
    rows = service.final_candidates()
    assert len(rows) == 4
    assert [row["final_instrument_type"] for row in rows] == [
        "SPOT", "SPOT", "FUTURES", "FUTURES"
    ]
    assert [row["final_ticker"] for row in rows] == [
        "AAA1", "BBB1", "NGV6", "ONZ6"
    ]
