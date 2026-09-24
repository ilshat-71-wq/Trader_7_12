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
