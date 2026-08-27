from services.spot_signal_contract import directional_rs, readiness_state, trigger_active, trigger_present
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


def test_readiness_contract_is_spot_only():
    assert readiness_state("WATCH", "LONG", "FIRST_PULLBACK", 100, 100) == "READY"
    assert readiness_state("WATCH", "SHORT", "FIRST_REBOUND", 100, 100) == "READY"
    assert readiness_state("WATCH", "LONG", "FIRST_PULLBACK", 100, 99.9) == "WAIT"
    assert readiness_state("READY", "SHORT", "FIRST_REBOUND", 100, 100.1) == "WAIT"
    assert readiness_state("CONFIRMED", "LONG", "FIRST_PULLBACK", 100, 101) == "CONFIRMED"


if __name__ == "__main__":
    tests = [
        test_directional_rs_contract_matches_live_pipeline,
        test_trigger_contract_matches_live_and_historical,
        test_invalid_trigger_is_never_active,
        test_readiness_contract_is_spot_only,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("ALL TESTS PASSED")
