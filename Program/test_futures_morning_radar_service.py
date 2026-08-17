"""
Trader_7_12 Pro

Tests for FuturesMorningRadarService.

The tests are offline and do not require BCS authorization.
"""

from datetime import date, datetime, timedelta

from services.futures_morning_radar_service import FuturesMorningRadarService


class FakeMappingService:
    def load(self):
        return [
            {
                "futures_ticker": "SRU6",
                "futures_class_code": "SPBFUT",
                "futures_expiry": "2026-09-01",
                "spot_ticker": "SBER",
                "spot_class_code": "TQBR",
                "spot_name": "Sberbank",
                "mapping_method": "EXPLICIT",
            },
            {
                "futures_ticker": "LKU6",
                "futures_class_code": "SPBFUT",
                "futures_expiry": "2026-09-01",
                "spot_ticker": "LKOH",
                "spot_class_code": "TQBR",
                "spot_name": "LUKOIL",
                "mapping_method": "EXPLICIT",
            },
        ]


class FakeRadarService:
    def analyze(self, ticker, class_code):
        data = {
            "SBER": {
                "version": "0.3",
                "status": "OK",
                "direction": "LONG",
                "radar_score": 78.0,
                "relative_strength": 0.031,
                "average_daily_money": 10_000_000_000,
                "signal": "LONG_WATCH",
            },
            "LKOH": {
                "version": "0.3",
                "status": "OK",
                "direction": "SHORT",
                "radar_score": 61.0,
                "relative_strength": -0.012,
                "average_daily_money": 10_000_000_000,
                "signal": "SHORT_WATCH",
            },
        }
        return data[ticker]



class FakeHistoryService:
    """Offline history stub for FuturesMorningRadarService tests."""

    def now(self):
        return datetime(2026, 8, 17, 10, 0, 0)

    def calculate_morning_money_volume(
        self,
        ticker,
        class_code,
        trading_date=None,
        timeframe_minutes=5,
    ):
        return {
            "SBER": 2_000_000_000,
            "LKOH": 1_000_000_000,
        }.get(ticker, 0.0)


def test_pipeline_maps_futures_to_spot_and_radar():
    service = FuturesMorningRadarService(
        mapping_service=FakeMappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    assert len(results) == 2
    assert results[0]["futures_ticker"] == "SRU6"
    assert results[0]["spot_ticker"] == "SBER"
    assert results[0]["direction"] == "LONG"
    assert results[0]["radar_score"] == 78.0
    assert results[0]["mapping_method"] == "EXPLICIT"


def test_pipeline_sorts_by_radar_score():
    service = FuturesMorningRadarService(
        mapping_service=FakeMappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    assert [item["radar_score"] for item in results] == [78.0, 61.0]
    assert [item["rank"] for item in results] == [1, 2]


def test_pipeline_limit():
    service = FuturesMorningRadarService(
        mapping_service=FakeMappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan(limit=1)

    assert len(results) == 1
    assert results[0]["futures_ticker"] == "SRU6"


def test_pipeline_skips_invalid_mapping():
    class InvalidMappingService:
        def load(self):
            return [
                None,
                {},
                {
                    "futures_ticker": "SRU6",
                    "futures_class_code": "SPBFUT",
                    "spot_ticker": "SBER",
                    "spot_class_code": "TQBR",
                    "futures_expiry": "2026-09-01",
                },
            ]

    service = FuturesMorningRadarService(
        mapping_service=InvalidMappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    assert len(results) == 1
    assert results[0]["futures_ticker"] == "SRU6"


def test_pipeline_keeps_radar_errors_without_stopping_scan():
    class ErrorRadarService:
        def analyze(self, ticker, class_code):
            if ticker == "SBER":
                raise RuntimeError("test radar failure")
            return FakeRadarService().analyze(ticker, class_code)

    service = FuturesMorningRadarService(
        mapping_service=FakeMappingService(),
        radar_service=ErrorRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    assert len(results) == 2
    assert results[0]["status"] == "OK"
    assert results[0]["futures_ticker"] == "LKU6"
    assert results[1]["status"] == "ERROR"
    assert results[1]["futures_ticker"] == "SRU6"


def test_pipeline_keeps_two_nearest_contracts_per_spot():
    today = date.today()
    nearest = today + timedelta(days=30)
    second = today + timedelta(days=60)
    third = today + timedelta(days=90)

    mappings = [
        {
            "futures_ticker": "SRZ6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": third.isoformat(),
            "spot_ticker": "SBER",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
        {
            "futures_ticker": "SRX6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": second.isoformat(),
            "spot_ticker": "SBER",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
        {
            "futures_ticker": "SRU6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": nearest.isoformat(),
            "spot_ticker": "SBER",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
        {
            "futures_ticker": "LKU6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": nearest.isoformat(),
            "spot_ticker": "LKOH",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
    ]

    class MappingService:
        def load(self):
            return mappings

    service = FuturesMorningRadarService(
        mapping_service=MappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    sber_results = [item for item in results if item["spot_ticker"] == "SBER"]

    assert len(sber_results) == 2
    assert [item["futures_ticker"] for item in sber_results] == ["SRU6", "SRX6"]
    assert [item["futures_expiry"] for item in sber_results] == [
        nearest.isoformat(),
        second.isoformat(),
    ]
    assert all(item["futures_ticker"] != "SRZ6" for item in sber_results)


def test_pipeline_skips_expired_contracts():
    expired = date.today() - timedelta(days=1)
    valid = date.today() + timedelta(days=30)

    mappings = [
        {
            "futures_ticker": "SROLD",
            "futures_class_code": "SPBFUT",
            "futures_expiry": expired.isoformat(),
            "spot_ticker": "SBER",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
        {
            "futures_ticker": "SRU6",
            "futures_class_code": "SPBFUT",
            "futures_expiry": valid.isoformat(),
            "spot_ticker": "SBER",
            "spot_class_code": "TQBR",
            "mapping_method": "EXPLICIT",
        },
    ]

    class MappingService:
        def load(self):
            return mappings

    service = FuturesMorningRadarService(
        mapping_service=MappingService(),
        radar_service=FakeRadarService(),
        history_service=FakeHistoryService(),
    )

    results = service.scan()

    assert len(results) == 1
    assert results[0]["futures_ticker"] == "SRU6"


if __name__ == "__main__":
    tests = [
        test_pipeline_maps_futures_to_spot_and_radar,
        test_pipeline_sorts_by_radar_score,
        test_pipeline_limit,
        test_pipeline_skips_invalid_mapping,
        test_pipeline_keeps_radar_errors_without_stopping_scan,
        test_pipeline_keeps_two_nearest_contracts_per_spot,
        test_pipeline_skips_expired_contracts,
    ]

    print("=" * 76)
    print("TRADER_7_12 PRO - FUTURES MORNING RADAR TEST")
    print("=" * 76)

    for test in tests:
        test()
        print("PASS", test.__name__)

    print()
    print("ALL TESTS PASSED")
    print("=" * 76)
