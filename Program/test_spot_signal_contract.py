from services.spot_signal_contract import (
    directional_rs,
    invalidation_active,
    lifecycle_state,
    readiness_state,
    setup_quality_score,
    trigger_active,
    trigger_crossed,
    trigger_present,
    trigger_state,
)
from services.historical_universe_replay_service import HistoricalUniverseReplayService
from services.morning_trading_pipeline_service import MorningTradingPipelineService


def test_directional_rs_contract_matches_live_pipeline():
    for direction, rs in (("LONG", 3.5), ("SHORT", -3.5), ("SHORT", 2.0), ("LONG", -2.0)):
        expected = directional_rs(rs, direction)
        actual = MorningTradingPipelineService._directional_rs({"relative_strength": rs, "direction": direction})
        assert actual == expected


def test_trigger_contract_matches_live_and_historical():
    cases = [
        ("LONG", 101, 100, True),
        ("LONG", 99.9, 100, False),
        ("SHORT", 99, 100, True),
        ("SHORT", 100.1, 100, False),
        ("LONG", 100, 100, True),
        ("SHORT", 100, 100, True),
    ]
    for direction, price, trigger, expected in cases:
        assert trigger_active(direction, price, trigger) is expected
        live = MorningTradingPipelineService._trigger_active({"direction": direction, "spot_price": price, "entry_trigger": trigger})
        historical = HistoricalUniverseReplayService._spot_trigger_active({"direction": direction, "spot_price": price, "entry_trigger": trigger})
        assert live is expected
        assert historical is expected


def test_invalid_trigger_is_never_active():
    for direction in ("LONG", "SHORT", "", None):
        assert trigger_present(0) is False
        assert trigger_active(direction, 100, 0) is False
        assert trigger_active(direction, 100, None) is False


def test_trigger_crossing_is_directional():
    assert trigger_crossed("LONG", 99, 100, 100)
    assert not trigger_crossed("LONG", 100, 101, 100)
    assert trigger_crossed("SHORT", 101, 100, 100)
    assert not trigger_crossed("SHORT", 100, 99, 100)


def test_trigger_state_distinguishes_armed_active_and_invalidated():
    assert trigger_state("LONG", 99, 100) == "ARMED"
    assert trigger_state("LONG", 100, 100) == "ACTIVE"
    assert trigger_state("LONG", 94, 100, 95) == "INVALIDATED"


def test_readiness_contract_is_spot_only():
    assert readiness_state("WATCH", "LONG", "FIRST_PULLBACK", 100, 100) == "READY"
    assert readiness_state("WATCH", "SHORT", "FIRST_REBOUND", 100, 100) == "READY"
    assert readiness_state("WATCH", "LONG", "FIRST_PULLBACK", 100, 99.9) == "WAIT"
    assert readiness_state("READY", "SHORT", "FIRST_REBOUND", 100, 100.1) == "WAIT"
    assert readiness_state("CONFIRMED", "LONG", "FIRST_PULLBACK", 100, 101) == "CONFIRMED"


def test_quality_combination_is_bounded_and_transparent():
    assert setup_quality_score(80) == 80
    assert setup_quality_score(80, 100, 100) == 88
    assert setup_quality_score(200, -10, 500) == 80


def test_lifecycle_wait_setup_never_becomes_active_signal():
    result = lifecycle_state("WAIT", "LONG", "PULLBACK", 100, 101)
    assert result["signal_state"] == "WAIT"
    assert result["trigger_active"] is True
    assert not result["signal_ready"]


def test_lifecycle_watch_without_trigger():
    result = lifecycle_state("WATCH", "LONG", "PULLBACK", 0, 99)
    assert result["signal_state"] == "WATCH"
    assert result["trigger_state"] == "WAITING"
    assert not result["signal_ready"]


def test_lifecycle_armed_before_trigger():
    result = lifecycle_state("READY", "LONG", "PULLBACK", 100, 99)
    assert result["signal_state"] == "ARMED"
    assert result["trigger_state"] == "ARMED"
    assert not result["signal_ready"]


def test_lifecycle_ready_after_stability():
    result = lifecycle_state("READY", "LONG", "PULLBACK", 100, 101, previous_price=99, consecutive_active=2, min_active_observations=2)
    assert result["signal_state"] == "READY"
    assert result["trigger_state"] == "ACTIVE"
    assert result["trigger_crossed"]
    assert result["signal_ready"]


def test_lifecycle_confirmed_is_spot_only():
    result = lifecycle_state("CONFIRMED", "SHORT", "REBOUND", 100, 99, consecutive_active=1)
    assert result["signal_state"] == "CONFIRMED"
    assert result["signal_confirmed"]


def test_lifecycle_invalidation_is_terminal_until_new_setup():
    invalidated = lifecycle_state("READY", "LONG", "PULLBACK", 100, 94, invalidation_level=95)
    assert invalidated["signal_state"] == "INVALIDATED"
    assert invalidated["trigger_state"] == "INVALIDATED"
    assert invalidated["signal_invalidated"]

    blocked = lifecycle_state("READY", "LONG", "PULLBACK", 100, 101, prior_signal_state="INVALIDATED")
    assert blocked["signal_state"] == "INVALIDATED"

    restarted = lifecycle_state("READY", "LONG", "PULLBACK", 100, 101, prior_signal_state="INVALIDATED", new_setup=True)
    assert restarted["signal_state"] == "READY"
    assert restarted["lifecycle_reset"]


def test_lifecycle_does_not_regress_ready_on_noise():
    result = lifecycle_state("READY", "LONG", "PULLBACK", 100, 99, prior_signal_state="READY", consecutive_active=0)
    assert result["signal_state"] == "READY"


def test_invalidation_direction():
    assert invalidation_active("LONG", 95, 95)
    assert not invalidation_active("LONG", 96, 95)
    assert invalidation_active("SHORT", 105, 105)
    assert not invalidation_active("SHORT", 104, 105)
