"""Canonical pure rules shared by live and historical SPOT analysis.

The contract is deterministic and network-free. It separates setup lifecycle,
trigger presence/activation, stability and signal readiness. Futures are never
used by this module.
"""

VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_SETUP_STATES = {"WAIT", "WATCH", "READY", "CONFIRMED"}
VALID_SIGNAL_STATES = {"WAIT", "WATCH", "ARMED", "READY", "CONFIRMED", "INVALIDATED"}
VALID_TRIGGER_STATES = {"WAITING", "ARMED", "ACTIVE", "INVALIDATED"}
VALID_SETUPS = {
    "FIRST_PULLBACK", "FIRST_REBOUND", "BREAKOUT", "PULLBACK", "REBOUND",
    "RETEST", "BREAKOUT_AFTER_PULLBACK", "BREAKDOWN_AFTER_REBOUND",
}

# Canonical monotonic progression for one setup lifecycle. INVALIDATED starts
# a terminal state; a new setup must receive a new lifecycle id externally.
STATE_ORDER = {
    "WAIT": 0,
    "WATCH": 1,
    "ARMED": 2,
    "READY": 3,
    "CONFIRMED": 4,
}


def normalize_direction(value):
    direction = str(value or "").upper()
    return direction if direction in VALID_DIRECTIONS else ""


def normalize_setup(value):
    setup = str(value or "NONE").upper()
    return setup if setup in VALID_SETUPS else "NONE"


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


def invalidation_active(direction, spot_price, invalidation_level):
    """Directional invalidation: LONG <= level, SHORT >= level."""
    direction = normalize_direction(direction)
    try:
        price = float(spot_price or 0)
        level = float(invalidation_level or 0)
    except (TypeError, ValueError):
        return False
    if price <= 0 or level <= 0:
        return False
    if direction == "LONG":
        return price <= level
    if direction == "SHORT":
        return price >= level
    return False


def trigger_state(direction, spot_price, entry_trigger, invalidation_level=None):
    """Classify trigger state without conflating presence and activation."""
    if invalidation_active(direction, spot_price, invalidation_level):
        return "INVALIDATED"
    if not trigger_present(entry_trigger):
        return "WAITING"
    if trigger_active(direction, spot_price, entry_trigger):
        return "ACTIVE"
    return "ARMED"


def setup_quality_score(setup_quality, breakout_quality=0, structure_quality=0):
    """Combine quality inputs without allowing a component to exceed 100."""
    values = []
    for value in (setup_quality, breakout_quality, structure_quality):
        try:
            values.append(max(0.0, min(100.0, float(value or 0))))
        except (TypeError, ValueError):
            values.append(0.0)
    if not any(values):
        return 0.0
    # Existing setup_quality remains the primary component; optional breakout
    # and structure evidence contribute only when supplied.
    if values[1] == 0 and values[2] == 0:
        return round(values[0], 2)
    return round(values[0] * 0.60 + values[1] * 0.20 + values[2] * 0.20, 2)


def readiness_state(setup_state, direction, setup, entry_trigger, spot_price):
    """Legacy-compatible readiness projection from the canonical contract."""
    state = str(setup_state or "WAIT").upper()
    direction = normalize_direction(direction)
    setup = normalize_setup(setup)
    active = trigger_active(direction, spot_price, entry_trigger)
    if direction not in VALID_DIRECTIONS or not trigger_present(entry_trigger) or not active:
        return "WAIT"
    if setup == "NONE":
        return "WAIT"
    if state == "CONFIRMED":
        return "CONFIRMED"
    if state in {"WATCH", "READY"}:
        return "READY"
    return "WAIT"


def lifecycle_state(
    setup_state,
    direction,
    setup,
    entry_trigger,
    spot_price,
    previous_price=None,
    prior_signal_state=None,
    consecutive_active=1,
    min_active_observations=1,
    invalidation_level=None,
    new_setup=False,
):
    """Return the canonical deterministic SPOT lifecycle.

    A lifecycle cannot move backwards merely because an observation is noisy.
    ``new_setup=True`` explicitly starts a new setup lifecycle. Invalidation is
    terminal for the current lifecycle; callers must create a new setup before
    it can become active again.
    """
    setup_state = str(setup_state or "WAIT").upper()
    direction = normalize_direction(direction)
    setup = normalize_setup(setup)
    prior = str(prior_signal_state or "").upper()
    valid_setup = direction in VALID_DIRECTIONS and setup != "NONE"
    present = trigger_present(entry_trigger)
    active = trigger_active(direction, spot_price, entry_trigger)
    crossed = trigger_crossed(direction, previous_price, spot_price, entry_trigger)
    invalidated = invalidation_active(direction, spot_price, invalidation_level)

    try:
        observations = max(0, int(consecutive_active or 0))
    except (TypeError, ValueError):
        observations = 0
    try:
        required = max(1, int(min_active_observations or 1))
    except (TypeError, ValueError):
        required = 1

    if not valid_setup:
        signal = "WAIT"
        trigger = "WAITING"
        reason = "invalid SPOT setup"
    elif invalidated:
        signal = "INVALIDATED"
        trigger = "INVALIDATED"
        reason = "SPOT setup invalidated; a new setup is required"
    elif prior == "INVALIDATED" and not new_setup:
        signal = "INVALIDATED"
        trigger = "WAITING" if not present else ("ACTIVE" if active else "ARMED")
        reason = "previous SPOT lifecycle is invalidated; waiting for a new setup"
    elif not present:
        signal = "WATCH"
        trigger = "WAITING"
        reason = "SPOT setup exists; waiting for a valid trigger level"
    elif not active:
        signal = "ARMED"
        trigger = "ARMED"
        reason = "SPOT trigger is armed; waiting for directional activation"
    elif setup_state == "CONFIRMED":
        signal = "CONFIRMED"
        trigger = "ACTIVE"
        reason = "SPOT setup is confirmed"
    elif observations >= required:
        signal = "READY"
        trigger = "ACTIVE"
        reason = "trigger active and stability requirement satisfied"
    else:
        signal = "ARMED"
        trigger = "ACTIVE"
        reason = "trigger active; waiting for stability"

    # Do not allow an old lifecycle to jump backwards unless explicitly reset.
    if not new_setup and prior in STATE_ORDER and signal in STATE_ORDER:
        if STATE_ORDER[signal] < STATE_ORDER[prior] and not invalidated:
            signal = prior
            if prior == "CONFIRMED":
                reason = "SPOT lifecycle remains confirmed"
            elif prior == "READY":
                reason = "SPOT lifecycle remains ready"

    return {
        "trigger_state": trigger,
        "trigger_present": present,
        "trigger_active": active,
        "trigger_crossed": crossed,
        "trigger_invalidated": invalidated,
        "signal_state": signal,
        "signal_ready": signal in {"READY", "CONFIRMED"},
        "signal_confirmed": signal == "CONFIRMED",
        "signal_invalidated": signal == "INVALIDATED",
        "stability_observations": observations,
        "stability_required": required,
        "signal_state_reason": reason,
        "prior_signal_state": prior,
        "lifecycle_reset": bool(new_setup),
    }
