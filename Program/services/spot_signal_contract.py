"""Canonical pure rules shared by live and historical SPOT analysis.

The contract is deterministic and network-free. It separates trigger level
presence, directional activation, crossing diagnostics and signal readiness.
"""

VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_SETUP_STATES = {"WAIT", "WATCH", "READY", "CONFIRMED"}
VALID_SIGNAL_STATES = {"WAIT", "READY", "CONFIRMED"}
VALID_TRIGGER_STATES = {"WAITING", "ARMED", "ACTIVE"}
VALID_SETUPS = {"FIRST_PULLBACK", "FIRST_REBOUND", "BREAKOUT", "PULLBACK", "REBOUND"}


def normalize_direction(value):
    direction = str(value or "").upper()
    return direction if direction in VALID_DIRECTIONS else ""


def directional_rs(relative_strength, direction):
    """Normalize RS so larger always means stronger support for direction."""
    try:
        rs = float(relative_strength or 0)
    except (TypeError, ValueError):
        rs = 0.0
    direction = normalize_direction(direction)
    if direction == "LONG":
        return rs
    if direction == "SHORT":
        return -rs
    return 0.0


def trigger_present(entry_trigger):
    try:
        return float(entry_trigger or 0) > 0
    except (TypeError, ValueError):
        return False


def trigger_active(direction, spot_price, entry_trigger):
    """Directional SPOT activation: LONG >= trigger, SHORT <= trigger."""
    direction = normalize_direction(direction)
    try:
        price = float(spot_price or 0)
        trigger = float(entry_trigger or 0)
    except (TypeError, ValueError):
        return False
    if price <= 0 or not trigger_present(trigger):
        return False
    if direction == "LONG":
        return price >= trigger
    if direction == "SHORT":
        return price <= trigger
    return False


def trigger_crossed(direction, previous_price, spot_price, entry_trigger):
    """Return True only when the current observation crosses the trigger."""
    direction = normalize_direction(direction)
    try:
        previous = float(previous_price)
        current = float(spot_price)
        trigger = float(entry_trigger)
    except (TypeError, ValueError):
        return False
    if direction not in VALID_DIRECTIONS or not trigger_present(trigger):
        return False
    if direction == "LONG":
        return previous < trigger <= current
    return previous > trigger >= current


def trigger_state(direction, spot_price, entry_trigger, previous_price=None):
    """Classify trigger state without conflating presence and activation."""
    if not trigger_present(entry_trigger):
        return "WAITING"
    if trigger_active(direction, spot_price, entry_trigger):
        return "ACTIVE"
    return "ARMED"


def readiness_state(setup_state, direction, setup, entry_trigger, spot_price):
    """Derive SPOT readiness without any futures input."""
    state = str(setup_state or "WAIT").upper()
    direction = normalize_direction(direction)
    setup = str(setup or "NONE").upper()
    active = trigger_active(direction, spot_price, entry_trigger)
    if direction not in VALID_DIRECTIONS or not trigger_present(entry_trigger) or not active:
        return "WAIT"
    if setup not in VALID_SETUPS:
        return "WAIT"
    if state == "CONFIRMED":
        return "CONFIRMED"
    if state in {"WATCH", "READY"}:
        return "READY"
    return "WAIT"


def lifecycle_state(setup_state, direction, setup, entry_trigger, spot_price,
                    previous_price=None, prior_signal_state=None,
                    consecutive_active=1, min_active_observations=1):
    """Return trigger lifecycle plus stable analytical readiness diagnostics.

    ``ARMED`` means a valid SPOT setup has a trigger but price has not reached
    it. ``ACTIVE`` means the directional level is active. ``READY`` is exposed
    after the configured consecutive-active observation requirement. This
    function does not use futures data and is safe for live and replay use.
    """
    setup_state = str(setup_state or "WAIT").upper()
    direction = normalize_direction(direction)
    setup = str(setup or "NONE").upper()
    valid_setup = direction in VALID_DIRECTIONS and setup in VALID_SETUPS
    present = trigger_present(entry_trigger)
    active = trigger_active(direction, spot_price, entry_trigger)
    crossed = trigger_crossed(direction, previous_price, spot_price, entry_trigger)
    try:
        observations = max(0, int(consecutive_active or 0))
    except (TypeError, ValueError):
        observations = 0
    try:
        required = max(1, int(min_active_observations or 1))
    except (TypeError, ValueError):
        required = 1

    if not valid_setup or not present:
        trigger = "WAITING"
        signal = "WAIT"
    elif not active:
        trigger = "ARMED"
        signal = "WAIT"
    else:
        trigger = "ACTIVE"
        if setup_state == "CONFIRMED":
            signal = "CONFIRMED"
        elif observations >= required:
            signal = "READY"
        else:
            signal = "WAIT"

    if not valid_setup:
        reason = "invalid SPOT setup"
    elif not present:
        reason = "no valid trigger level"
    elif not active:
        reason = "SPOT setup is armed; waiting for directional trigger"
    elif signal == "CONFIRMED":
        reason = "SPOT setup is confirmed"
    elif signal == "READY" and crossed:
        reason = "trigger crossed and stability requirement satisfied"
    elif signal == "READY":
        reason = "trigger active and stability requirement satisfied"
    else:
        reason = "trigger active; waiting for stability"

    return {
        "trigger_state": trigger,
        "trigger_active": active,
        "trigger_crossed": crossed,
        "signal_state": signal,
        "signal_ready": signal in {"READY", "CONFIRMED"},
        "signal_confirmed": signal == "CONFIRMED",
        "stability_observations": observations,
        "stability_required": required,
        "signal_state_reason": reason,
        "prior_signal_state": str(prior_signal_state or "").upper(),
    }
