from services.move_radar_service import MoveRadarService


def item(ticker, change, used, accel, probability, signal="LONG"):
    return {
        "spot_ticker": ticker,
        "change_percent": change,
        "atr_used_percent": used,
        "money_acceleration": accel,
        "signal_probability": probability,
        "signal": signal,
    }


def test_start_requires_unused_atr_and_acceleration():
    row = MoveRadarService.classify(item("VGSB", 5.0, 25.0, 928.0, 91.7))
    assert row["move_phase"] == "START"


def test_exhaustion_after_more_than_one_atr():
    row = MoveRadarService.classify(item("RTSBP", -13.92, 139.0, -91.9, 90.9, "SHORT"))
    assert row["move_phase"] == "EXHAUSTION"


def test_late_phase_between_70_and_100_percent_atr():
    row = MoveRadarService.classify(item("TEST", -2.0, 85.0, -5.0, 90.0, "SHORT"))
    assert row["move_phase"] == "LATE"


def test_developing_phase_is_directionally_aligned():
    row = MoveRadarService.classify(item("TEST", 2.0, 55.0, 5.0, 82.0, "LONG"))
    assert row["move_phase"] == "DEVELOPING"


def test_direction_conflict_is_not_presented_as_move():
    assert MoveRadarService.classify(item("EUTR", 12.6, 2.0, 10.0, 87.5, "SHORT")) is None


def test_small_move_is_not_a_move_candidate():
    assert MoveRadarService.classify(item("TEST", 0.7, 20.0, 500.0, 95.0, "LONG")) is None



def test_non_finite_move_metrics_are_rejected():
    assert MoveRadarService.classify(item("NAN", float("nan"), 20.0, 100.0, 95.0)) is None
    assert MoveRadarService.classify(item("INF", 2.0, float("inf"), 100.0, 95.0)) is None
    assert MoveRadarService.classify(item("BADPROB", 2.0, 20.0, 100.0, float("nan"))) is None


def test_extreme_acceleration_does_not_change_phase_or_crash():
    row = MoveRadarService.classify(item("OUTLIER", 2.0, 20.0, 32591.2, 93.6))
    assert row["move_phase"] == "START"
    assert row["directional_acceleration"] == 32591.2
