from services.morning_scanner_runner import MorningScannerRunner


class FakePipeline:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def scan(self, limit=3):
        self.calls.append(limit)
        return self.result[:limit]


def test_runner_delegates_to_pipeline():
    pipeline = FakePipeline([{"futures_ticker": "SBERM6", "direction": "LONG"}])
    runner = MorningScannerRunner(pipeline)
    result = runner.run(limit=2)
    assert result == [{"futures_ticker": "SBERM6", "direction": "LONG"}]
    assert pipeline.calls == [2]


def test_runner_limits_to_three_by_default():
    pipeline = FakePipeline([
        {"futures_ticker": "A"},
        {"futures_ticker": "B"},
        {"futures_ticker": "C"},
        {"futures_ticker": "D"},
    ])
    runner = MorningScannerRunner(pipeline)
    assert len(runner.run()) == 3


def test_runner_allows_empty_result():
    runner = MorningScannerRunner(FakePipeline([]))
    assert runner.run() == []


def test_runner_does_not_submit_orders():
    pipeline = FakePipeline([{"futures_ticker": "SBERM6"}])
    runner = MorningScannerRunner(pipeline)
    assert not hasattr(pipeline, "submit_order")
    assert runner.run(limit=1)[0]["futures_ticker"] == "SBERM6"


def run_tests():
    print("=" * 76)
    print("TRADER_7_12 PRO - MORNING SCANNER RUNNER TEST")
    print("=" * 76)
    tests = [
        test_runner_delegates_to_pipeline,
        test_runner_limits_to_three_by_default,
        test_runner_allows_empty_result,
        test_runner_does_not_submit_orders,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("=" * 76)
    print("ALL TESTS PASSED")
    print("=" * 76)


if __name__ == "__main__":
    run_tests()
