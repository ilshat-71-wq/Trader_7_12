"""Unit tests for FuturesConfirmationService."""

from services.futures_confirmation_service import FuturesConfirmationService


def make_trades(count=20, start=100.0, step=0.5, volume=1000):
    return [
        {
            "price": start + index * step,
            "volume": volume,
        }
        for index in range(count)
    ]


def test_confirmed_long():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(),
        "LONG",
    )

    assert result["confirmation"] == "CONFIRMED"
    assert result["status"] == "OK"
    assert result["direction"] == "LONG"
    assert result["score"] > 0


def test_confirmed_short():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(start=100.0, step=-0.5),
        "SHORT",
    )

    assert result["confirmation"] == "CONFIRMED"
    assert result["direction"] == "SHORT"


def test_conflicting_direction_is_blocked():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(),
        "SHORT",
    )

    assert result["confirmation"] == "BLOCKED"
    assert result["status"] == "BLOCKED"
    assert "conflicts" in result["reason"]


def test_insufficient_trades_are_blocked():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(count=5),
        "LONG",
    )

    assert result["confirmation"] == "BLOCKED"
    assert result["trade_count"] == 5


def test_insufficient_money_volume_is_blocked():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(volume=1),
        "LONG",
    )

    assert result["confirmation"] == "BLOCKED"
    assert "money volume" in result["reason"]


def test_no_data():
    result = FuturesConfirmationService.analyze_trades([], "LONG")

    assert result["confirmation"] == "NO_DATA"
    assert result["status"] == "NO_DATA"
    assert result["trade_count"] == 0


def test_invalid_spot_direction_is_blocked():
    result = FuturesConfirmationService.analyze_trades(
        make_trades(),
        "NONE",
    )

    assert result["confirmation"] == "BLOCKED"
    assert result["status"] == "BLOCKED"


def run_all_tests():
    tests = [
        test_confirmed_long,
        test_confirmed_short,
        test_conflicting_direction_is_blocked,
        test_insufficient_trades_are_blocked,
        test_insufficient_money_volume_is_blocked,
        test_no_data,
        test_invalid_spot_direction_is_blocked,
    ]

    print("=" * 76)
    print("TRADER_7_12 PRO - FUTURES CONFIRMATION SERVICE TEST")
    print("=" * 76)

    for test in tests:
        test()
        print("PASS", test.__name__)

    print()
    print("ALL TESTS PASSED")
    print("=" * 76)


if __name__ == "__main__":
    run_all_tests()
