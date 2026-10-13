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


def spot_item(m1_state, triggered=True, setup_state="WATCH", h1="NEAR_H1_SUPPORT", signal="LONG"):
    return {
        "instrument_type": "SPOT",
        "spot_ticker": "SBER",
        "signal": signal,
        "signal_probability": 88.0,
        "daily_qualified": True,
        "h1_level_context": h1,
        "setup_state": setup_state,
        "m1_entry_state": m1_state,
        "m1_entry_triggered": triggered,
        "liquidity_gate": True,
        "atr_used_percent": 25.0,
        "money_acceleration": 100.0,
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


def test_entry_radar_oi_action_conflict_is_directional():
    # Long liquidation is adverse to LONG but directionally consistent with SHORT.
    assert EntryRadarService.state(item(83, signal="LONG", action="LONG_LIQUIDATION")) == "AVOID"
    assert EntryRadarService.state(item(83, signal="SHORT", action="LONG_LIQUIDATION")) == "ENTER"

    # Short covering is adverse to SHORT but directionally consistent with LONG.
    assert EntryRadarService.state(item(83, signal="SHORT", action="SHORT_COVERING")) == "AVOID"
    assert EntryRadarService.state(item(83, signal="LONG", action="SHORT_COVERING")) == "ENTER"



def test_spot_entry_high_probability_cannot_override_atr_exhaustion():
    item = spot_item("CONFIRMED")
    item["atr_used_percent"] = 151.0
    item["signal_probability"] = 99.0
    assert EntryRadarService.state(item) == "AVOID"
    assert "ATR used" in EntryRadarService.reason(item)


def test_spot_entry_blocks_explicit_exhaustion_phase():
    item = spot_item("CONFIRMED")
    item["move_phase"] = "EXHAUSTION"
    assert EntryRadarService.state(item) == "AVOID"


def test_spot_entry_missing_liquidity_or_atr_is_not_enter():
    item = spot_item("CONFIRMED")
    item["liquidity_gate"] = None
    assert EntryRadarService.state(item) == "WATCH"
    item = spot_item("CONFIRMED")
    item.pop("atr_used_percent")
    assert EntryRadarService.state(item) == "WATCH"


def test_entry_probability_nan_is_not_an_entry():
    item = spot_item("CONFIRMED")
    item["signal_probability"] = float("nan")
    assert EntryRadarService.state(item) == "WATCH"


def test_spot_entry_with_sub_80_score_is_wait_not_enter():
    item = spot_item("CONFIRMED")
    item["signal_probability"] = 74.0
    assert EntryRadarService.state(item) == "WAIT"
