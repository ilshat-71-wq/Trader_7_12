"""Canonical pure rules shared by live and historical SPOT analysis."""


VALID_DIRECTIONS = {"LONG", "SHORT"}
VALID_SETUP_STATES = {"WAIT", "WATCH", "READY", "CONFIRMED"}


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


def readiness_state(setup_state, direction, setup, entry_trigger, spot_price):
    """Derive SPOT readiness without any futures input."""
    state = str(setup_state or "WAIT").upper()
    direction = normalize_direction(direction)
    setup = str(setup or "NONE").upper()
    active = trigger_active(direction, spot_price, entry_trigger)
    if direction not in VALID_DIRECTIONS:
        return "WAIT"
    if not trigger_present(entry_trigger) or not active:
        return "WAIT"
    if setup not in {"FIRST_PULLBACK", "FIRST_REBOUND", "BREAKOUT", "PULLBACK", "REBOUND"}:
        return "WAIT"
    if state == "CONFIRMED":
        return "CONFIRMED"
    if state in {"WATCH", "READY"}:
        return "READY"
    return "WAIT"
