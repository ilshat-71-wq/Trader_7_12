from services.signal_probability_service import SignalProbabilityService


def test_missing_or_non_finite_price_change_is_incomplete():
    service = SignalProbabilityService()
    for value in (None, float("nan"), float("inf"), "not-a-number"):
        result = service.spot({"change_percent": value})
        assert result["signal"] == "NEUTRAL"
        assert result["probability"] == 50.0
        assert result["signal_status"] == "INCOMPLETE"


def test_extreme_acceleration_remains_finite_and_is_not_win_probability():
    service = SignalProbabilityService()
    row = {
        "change_percent": 1.9,
        "relative_strength": -0.22,
        "money_acceleration": 32591.2,
        "money_per_minute": 83500.0,
        "recent_money_per_minute": 120000.0,
        "daily_structure": "UP",
    }
    result = service.spot(row)
    assert 50.0 <= result["probability"] <= 99.0
    assert result["signal_status"] == "AVAILABLE"

def test_opposing_acceleration_reduces_directional_score_without_forcing_a_reversal():
    service = SignalProbabilityService()
    base = {
        "change_percent": 1.9,
        "relative_strength": 0.4,
        "money_per_minute": 83_500.0,
        "recent_money_per_minute": 120_000.0,
        "daily_structure": "UP",
    }
    aligned = service.spot(dict(base, money_acceleration=80.0))
    opposing = service.spot(dict(base, money_acceleration=-80.0))

    assert aligned["long_probability"] > opposing["long_probability"]
    # Acceleration is one feature, not an automatic reverse-signal command.
    assert opposing["signal"] in {"LONG", "NEUTRAL"}

