from services.historical_candidate_ranker_service import HistoricalCandidateRankerService


def test_futures_fields_do_not_change_historical_score():
    base = {
        "direction": "LONG",
        "trend_state": "UPTREND",
        "trend_change_percent": 2.0,
        "relative_strength_available": True,
        "relative_strength_data": {"excess_change_percent": 1.5},
        "relative_strength": 15.0,
        "setup": "FIRST_PULLBACK",
        "setup_state": "READY",
        "entry_trigger": 100.0,
        "spot_setup_state": "READY",
        "spot_entry_trigger": 100.0,
        "spot_ready_time": "08:30:00",
        "average_daily_money": 300_000_000,
        "futures_average_daily_money": 100_000_000,
        "futures_price": 100.0,
        "futures_confirmation": {"status": "OK", "score": 100},
    }

    changed = dict(base)
    changed.update(
        {
            "futures_average_daily_money": 9_999_999_999,
            "futures_price": 999.0,
            "futures_confirmation": {"status": "BLOCKED", "score": 0},
            "confirmation_time": "12:55:00",
        }
    )

    assert HistoricalCandidateRankerService.score(base) == HistoricalCandidateRankerService.score(changed)


def test_spot_readiness_changes_historical_score():
    wait = {
        "direction": "LONG",
        "trend_state": "UPTREND",
        "trend_change_percent": 2.0,
        "relative_strength_available": True,
        "relative_strength_data": {"excess_change_percent": 1.0},
        "setup": "FIRST_PULLBACK",
        "setup_state": "WAIT",
        "entry_trigger": 0.0,
        "average_daily_money": 300_000_000,
    }
    ready = dict(wait)
    ready.update(
        {
            "setup_state": "READY",
            "entry_trigger": 100.0,
            "spot_setup_state": "READY",
            "spot_entry_trigger": 100.0,
            "spot_ready_time": "08:30:00",
        }
    )

    assert HistoricalCandidateRankerService.score(ready) > HistoricalCandidateRankerService.score(wait)
