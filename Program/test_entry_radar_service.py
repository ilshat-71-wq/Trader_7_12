from services.entry_radar_service import EntryRadarService


def item(probability, signal="LONG", low=100.0, high=110.0, action="FLOW_ONLY", delta=0.0):
    return {
        "signal_probability": probability,
        "signal": signal,
        "money_flow_zone_low": low,
        "money_flow_zone_high": high,
        "money_flow_position_action": action,
        "signal_probability_delta": delta,
    }


def test_entry_radar_states_match_design():
    assert EntryRadarService.state(item(83)) == "ENTER"
    assert EntryRadarService.state(item(76, delta=-7)) == "WAIT"
    assert EntryRadarService.state(item(73, delta=-7)) == "WAIT"
    assert EntryRadarService.state(item(70, delta=-16)) == "WAIT"
    assert EntryRadarService.state(item(63, signal="SHORT", delta=-32)) == "WATCH"
    assert EntryRadarService.state(item(61, action="LONG_LIQUIDATION", delta=-18)) == "AVOID"


def test_entry_radar_requires_zone():
    assert EntryRadarService.state(item(85, low=None, high=None)) == "WATCH"


def spot_item(m1_state, triggered=True, setup_state="WATCH", h1="NEAR_H1_SUPPORT"):
    return {
        "instrument_type": "SPOT",
        "spot_ticker": "SBER",
        "signal": "LONG",
        "signal_probability": 88.0,
        "daily_qualified": True,
        "h1_level_context": h1,
        "setup_state": setup_state,
        "m1_entry_state": m1_state,
        "m1_entry_triggered": triggered,
    }


def test_spot_entry_uses_d1_h1_m5_m1_pipeline():
    assert EntryRadarService.state(spot_item("CONFIRMED")) == "ENTER"
    assert EntryRadarService.state(spot_item("ARMED", triggered=False)) == "WAIT"
    assert EntryRadarService.state(spot_item("WAIT")) == "WATCH"


def test_spot_entry_never_uses_synthetic_zone():
    item = spot_item("CONFIRMED")
    assert "money_flow_zone_low" not in item
    assert EntryRadarService.state(item) == "ENTER"


def test_spot_entry_requires_directionally_aligned_h1_level():
    assert EntryRadarService.state(spot_item("CONFIRMED", h1="NEAR_H1_RESISTANCE")) == "WATCH"
    assert EntryRadarService.state(spot_item("CONFIRMED", signal="SHORT", h1="NEAR_H1_RESISTANCE")) == "ENTER"
