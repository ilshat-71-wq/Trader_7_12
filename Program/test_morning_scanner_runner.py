from services.morning_scanner_runner import MorningScannerRunner


class FakePipeline:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def scan(self, limit=3):
        self.calls.append(limit)
        return self.result[:limit]


def test_runner_delegates_to_pipeline():
    pipeline = FakePipeline([{"spot_ticker": "SBER", "direction": "LONG", "setup_state": "WAIT"}])
    runner = MorningScannerRunner(pipeline)
    result = runner.run(limit=2)
    assert result == [{"spot_ticker": "SBER", "direction": "LONG", "setup_state": "WAIT"}]
    assert pipeline.calls == [2]


def test_runner_limits_to_three_by_default():
    pipeline = FakePipeline([
        {"spot_ticker": "A"},
        {"spot_ticker": "B"},
        {"spot_ticker": "C"},
        {"spot_ticker": "D"},
    ])
    runner = MorningScannerRunner(pipeline)
    assert len(runner.run()) == 3


def test_runner_allows_empty_result():
    runner = MorningScannerRunner(FakePipeline([]))
    assert runner.run() == []


def test_runner_is_read_only():
    pipeline = FakePipeline([{"spot_ticker": "SBER", "direction": "LONG"}])
    runner = MorningScannerRunner(pipeline)
    assert not hasattr(pipeline, "submit_order")
    assert runner.run(limit=1)[0]["spot_ticker"] == "SBER"


def test_runner_preserves_watchlist_state():
    pipeline = FakePipeline([{"spot_ticker": "AFLT", "setup_state": "WATCH", "opportunity_score": 88.2}])
    result = MorningScannerRunner(pipeline).run(limit=1)
    assert result[0]["setup_state"] == "WATCH"
    assert result[0]["opportunity_score"] == 88.2


def run_tests():
    print("=" * 76)
    print("TRADER_7_12 PRO - SPOT OPPORTUNITY WATCHLIST RUNNER TEST")
    print("=" * 76)
    tests = [
        test_runner_delegates_to_pipeline,
        test_runner_limits_to_three_by_default,
        test_runner_allows_empty_result,
        test_runner_is_read_only,
        test_runner_preserves_watchlist_state,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("=" * 76)
    print("ALL TESTS PASSED")
    print("=" * 76)


if __name__ == "__main__":
    run_tests()
