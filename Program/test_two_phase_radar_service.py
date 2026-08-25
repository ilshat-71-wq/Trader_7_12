"""Offline tests for the two-phase radar orchestration."""

from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService


class FakeBaseRadar:
    def calculate(self, ticker, class_code):
        scores = {"A": 90, "B": 80, "C": 70, "D": 60, "E": 50, "F": 40}
        score = scores.get(ticker, 10)
        return {
            "daily": {"trend": {"direction": "LONG", "days": 3, "change_percent": 2.0}},
            "money": {"average_daily_money_volume": score * 1_000_000},
        }


class FakeInstrumentRadar:
    radar_service = FakeBaseRadar()

    @staticmethod
    def calculate_trend_score(trend):
        return 50

    @staticmethod
    def calculate_money_score(money):
        return float(money.get("average_daily_money_volume", 0)) / 1_000_000

    @staticmethod
    def calculate_radar_score(trend_score, money_score):
        return trend_score + money_score


class FakeMapping:
    GROUPS = {
        "A": "MOEX_STOCK",
        "B": "GAS",
        "C": "OIL",
        "D": "USDRUB",
        "E": "GOLD",
        "F": "MOEX_STOCK",
    }

    def load(self):
        return [
            {
                "spot_ticker": ticker,
                "spot_class_code": "SPOT",
                "spot_group": self.GROUPS[ticker],
                "futures_ticker": f"F{ticker}",
                "futures_class_code": "SPBFUT",
                "futures_expiry": "2099-01-01",
            }
            for ticker in "ABCDEF"
        ]


class FakeSession:
    def now(self):
        from datetime import datetime
        return datetime(2099, 1, 1, 10, 0, 0)

    def get_session(self):
        return "MORNING"

    def get_trading_day(self):
        from datetime import date
        return date(2099, 1, 1)


class FakeSessionMoney:
    def calculate(self, ticker, class_code, trading_date=None, timeframe_minutes=5, session=None):
        values = {
            "A": 600_000_000,
            "B": 500_000_000,
            "C": 400_000_000,
            "D": 300_000_000,
            "E": 200_000_000,
            "F": 100_000_000,
        }
        money = values.get(ticker, 0)
        return {
            "session": session,
            "money_volume": money,
            "elapsed_minutes": 180,
            "expected_minutes": 180,
            "money_per_minute": money / 180,
        }


class TestableRadar(TwoPhaseFuturesMorningRadarService):
    def __init__(self):
        super().__init__(
            mapping_service=FakeMapping(),
            radar_service=FakeInstrumentRadar(),
            session_service=FakeSession(),
            session_money_service=FakeSessionMoney(),
        )
        self.deep_calls = []

    def _select_current_contracts(self, mappings):
        return mappings

    def _load_mappings_cached(self):
        return FakeMapping().load()

    def _preliminary_scan(self, mappings):
        return super()._preliminary_scan(mappings)

    def _deep_result(self, item):
        self.deep_calls.append(item)

    def _make_deep_results(self, mappings):
        self.deep_calls = [m["spot_ticker"] for m in mappings]


def test_preliminary_keeps_top_five():
    service = TestableRadar()
    mappings = FakeMapping().load()
    preliminary = service._preliminary_scan(mappings)
    ranked = sorted(
        preliminary.items(),
        key=lambda item: item[1]["radar_score"],
        reverse=True,
    )

    assert [key for key, _value in ranked[:5]] == [
        ("A", "SPOT"),
        ("B", "SPOT"),
        ("C", "SPOT"),
        ("D", "SPOT"),
        ("E", "SPOT"),
    ]


def test_deep_limit_is_five():
    assert TestableRadar.DEEP_SPOT_LIMIT == 5


if __name__ == "__main__":
    test_preliminary_keeps_top_five()
    print("PASS test_preliminary_keeps_top_five")
    test_deep_limit_is_five()
    print("PASS test_deep_limit_is_five")
    print("ALL TESTS PASSED")
