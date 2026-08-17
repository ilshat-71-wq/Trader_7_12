"""
Trader_7_12 Pro

Instrument Morning Radar Service v0.3
Deterministic unit test.

Тест не обращается к BCS и не требует авторизации.
Живой market-data запуск выполняется отдельной командой.
"""

from datetime import date

from services.instrument_morning_radar_service import (
    InstrumentMorningRadarService
)


class DummyRadar:
    """Создаёт сервис без сетевого доступа."""

    def __init__(self):
        self.service = InstrumentMorningRadarService()


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(
            f"{message}: expected {expected!r}, got {actual!r}"
        )


def assert_close(actual, expected, tolerance=0.0001, message="value"):
    if abs(float(actual) - float(expected)) > tolerance:
        raise AssertionError(
            f"{message}: expected {expected}, got {actual}"
        )


def test_utc_trading_date():
    service = DummyRadar().service

    value = "2026-08-12T21:00:00Z"
    result = service._utc_trading_date(value)

    assert_equal(
        result,
        date(2026, 8, 12),
        "BCS D-candle trading date must stay on UTC date"
    )


def test_close_map():
    service = DummyRadar().service

    candles = [
        {
            "time": "2026-08-11T21:00:00Z",
            "close": 100,
        },
        {
            "time": "2026-08-12T21:00:00Z",
            "close": 105,
        },
        {
            "time": "2026-08-13T21:00:00Z",
            "close": 110,
        },
    ]

    result = service._build_close_map(candles)

    assert_equal(len(result), 3, "close map size")
    assert_equal(result[date(2026, 8, 12)], 105.0, "close map value")


def test_relative_strength():
    service = DummyRadar().service

    instrument = [
        {"time": "2026-08-11T21:00:00Z", "close": 100},
        {"time": "2026-08-12T21:00:00Z", "close": 110},
    ]

    benchmark = [
        {"time": "2026-08-11T21:00:00Z", "close": 1000},
        {"time": "2026-08-12T21:00:00Z", "close": 1050},
    ]

    result = service.calculate_relative_strength_from_candles(
        instrument,
        benchmark
    )

    # Instrument +10%, benchmark +5%, RS = +5 percentage points.
    assert_equal(result["status"], "OK", "RS status")
    assert_close(result["relative_strength"], 5.0, message="RS")
    assert_equal(result["previous_date"], "2026-08-11", "RS previous date")
    assert_equal(result["current_date"], "2026-08-12", "RS current date")
    assert_equal(
        result["benchmark"],
        "IMOEX2/IRUS2",
        "RS benchmark"
    )


def test_relative_strength_no_common_history():
    service = DummyRadar().service

    result = service.calculate_relative_strength_from_candles(
        [
            {"time": "2026-08-11T21:00:00Z", "close": 100},
        ],
        [
            {"time": "2026-08-12T21:00:00Z", "close": 1000},
        ]
    )

    assert_equal(result["status"], "NO_DATA", "RS no-data status")
    assert_equal(result["relative_strength"], 0.0, "RS no-data value")


def test_scores():
    service = DummyRadar().service

    trend = {
        "direction": "LONG",
        "state": "UPTREND",
        "days": 3,
        "change_percent": 3.0,
    }

    trend_score = service.calculate_trend_score(trend)
    money_score = service.calculate_money_score(
        {"average_daily_money_volume": 100_000_000}
    )
    radar_score = service.calculate_radar_score(
        trend_score,
        money_score
    )

    # 20 direction + 25 state + 15 days + 15 change = 75.
    assert_equal(trend_score, 75, "trend score")
    assert_equal(money_score, 35, "money score")
    assert_close(radar_score, 73.33, message="radar score")


def test_signal():
    service = DummyRadar().service

    assert_equal(
        service._preliminary_signal(75, "LONG"),
        "LONG_WATCH",
        "long signal"
    )
    assert_equal(
        service._preliminary_signal(75, "SHORT"),
        "SHORT_WATCH",
        "short signal"
    )
    assert_equal(
        service._preliminary_signal(55, "NONE"),
        "WATCH",
        "neutral watch signal"
    )
    assert_equal(
        service._preliminary_signal(40, "LONG"),
        "SKIP",
        "skip signal"
    )


def test_scan_sorting():
    service = DummyRadar().service

    def fake_analyze(ticker, class_code):
        values = {
            "SBER": 60,
            "LKOH": 85,
            "ROSN": 72,
        }
        return {
            "ticker": ticker,
            "class_code": class_code,
            "status": "OK",
            "radar_score": values[ticker],
        }

    service.analyze = fake_analyze

    results = service.scan(
        {
            "SBER": "SPBRU",
            "LKOH": "SPBRU",
            "ROSN": "SPBRU",
        }
    )

    assert_equal(results[0]["ticker"], "LKOH", "rank 1")
    assert_equal(results[1]["ticker"], "ROSN", "rank 2")
    assert_equal(results[2]["ticker"], "SBER", "rank 3")
    assert_equal(results[0]["rank"], 1, "rank field 1")
    assert_equal(results[2]["rank"], 3, "rank field 3")


def main():
    tests = [
        test_utc_trading_date,
        test_close_map,
        test_relative_strength,
        test_relative_strength_no_common_history,
        test_scores,
        test_signal,
        test_scan_sorting,
    ]

    print()
    print("=" * 72)
    print("TRADER_7_12 PRO - INSTRUMENT MORNING RADAR v0.3 TEST")
    print("=" * 72)

    for test in tests:
        test()
        print(f"PASS  {test.__name__}")

    print()
    print("ALL TESTS PASSED")
    print("=" * 72)


if __name__ == "__main__":
    main()
