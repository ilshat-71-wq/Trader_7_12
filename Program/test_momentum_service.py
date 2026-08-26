from services.momentum_service import MomentumService


def test_strong_long_momentum():
    result = MomentumService().analyze({"open": 100, "high": 110, "low": 99, "close": 109, "volume": 200, "money_volume": 21_800}, average_volume=100, average_money_volume=10_000, previous_high=105, previous_low=95)
    assert result["momentum_score"] >= 75
    assert result["breakout_strength"] == 100
    assert result["true_breakout"] is True
    assert result["signal"] == "STRONG_LONG"


def test_strong_short_momentum():
    result = MomentumService().analyze({"open": 110, "high": 111, "low": 99, "close": 100, "volume": 200, "money_volume": 20_000}, average_volume=100, average_money_volume=10_000, previous_high=115, previous_low=105)
    assert result["momentum_score"] <= -75
    assert result["breakout_strength"] == -100
    assert result["true_breakout"] is True
    assert result["signal"] == "STRONG_SHORT"


def test_volume_does_not_create_direction_on_flat_candle():
    result = MomentumService().analyze({"open": 100, "high": 100.1, "low": 99.9, "close": 100, "volume": 1_000, "money_volume": 100_000}, average_volume=100, average_money_volume=10_000)
    assert result["signal"] == "NO_SIGNAL"
    assert result["breakout_strength"] == 0


def test_money_volume_ratio_is_reported():
    result = MomentumService().analyze({"open": 100, "high": 102, "low": 99, "close": 101, "volume": 150, "money_volume": 15_150}, average_volume=100, average_money_volume=10_000)
    assert result["volume_ratio"] == 1.5
    assert result["money_volume_ratio"] == 1.51
