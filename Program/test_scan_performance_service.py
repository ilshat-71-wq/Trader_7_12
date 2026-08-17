from services.scan_performance_service import ScanPerformanceService



def test_empty_report_is_valid():
    service = ScanPerformanceService()
    report = service.finish()
    assert report.total_seconds >= 0
    assert report.target_seconds == 30.0
    assert report.within_target is True



def test_stage_is_recorded():
    service = ScanPerformanceService()
    stage = service.start_stage("SPOT")
    service.finish_stage()
    assert stage.finished_at is not None
    assert service.report.stage("SPOT").elapsed_seconds >= 0



def test_starting_new_stage_finishes_previous_stage():
    service = ScanPerformanceService()
    first = service.start_stage("UNIVERSE")
    second = service.start_stage("SPOT")
    service.finish()
    assert first.finished_at is not None
    assert second.finished_at is not None
    assert [item.name for item in service.report.stages] == ["UNIVERSE", "SPOT"]



def test_classification():
    assert ScanPerformanceService.classify(5) == "EXCELLENT"
    assert ScanPerformanceService.classify(20) == "GOOD"
    assert ScanPerformanceService.classify(30) == "TARGET"
    assert ScanPerformanceService.classify(31) == "SLOW"



def test_invalid_target_is_rejected():
    try:
        ScanPerformanceService(0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    tests = [
        test_empty_report_is_valid,
        test_stage_is_recorded,
        test_starting_new_stage_finishes_previous_stage,
        test_classification,
        test_invalid_target_is_rejected,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("ALL TESTS PASSED")
