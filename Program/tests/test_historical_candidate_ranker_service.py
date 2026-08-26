from services.futures_trade_candidate_service import FuturesTradeCandidateService
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


def test_production_candidate_score_ignores_futures_confirmation():
    base = {
        "direction": "SHORT",
        "spot_group": "MOEX_STOCK",
        "relative_strength": -1.5,
        "relative_strength_status": "OK",
        "spot_session_activity_ratio": 2.0,
        "spot_money_per_minute": 20_000_000,
        "spot_money_volume": 400_000_000,
        "change_percent": -2.0,
        "setup_quality_score": 60.0,
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
        }
    )

    assert FuturesTradeCandidateService.calculate_score(base) == FuturesTradeCandidateService.calculate_score(changed)


def test_production_rank_tie_breaks_relative_strength_in_trade_direction(monkeypatch):
    service = FuturesTradeCandidateService()

    radars = [
        {
            "direction": "SHORT",
            "spot_group": "MOEX_STOCK",
            "spot_ticker": "WEAK_A",
            "spot_session_activity_ratio": 2.0,
            "spot_money_per_minute": 20_000_000,
            "spot_money_volume": 400_000_000,
            "relative_strength": -1.0,
            "relative_strength_status": "OK",
            "setup_quality_score": 50.0,
        },
        {
            "direction": "SHORT",
            "spot_group": "MOEX_STOCK",
            "spot_ticker": "WEAK_B",
            "spot_session_activity_ratio": 2.0,
            "spot_money_per_minute": 20_000_000,
            "spot_money_volume": 400_000_000,
            "relative_strength": -3.0,
            "relative_strength_status": "OK",
            "setup_quality_score": 50.0,
        },
    ]

    def fixed_candidate(radar):
        return {
            "candidate_score": 80.0,
            "spot_session_activity_ratio": 2.0,
            "spot_money_per_minute": 20_000_000,
            "spot_money_volume": 400_000_000,
            "relative_strength": radar["relative_strength"],
            "direction": radar["direction"],
            "setup_quality_score": 50.0,
            "spot_ticker": radar["spot_ticker"],
        }

    monkeypatch.setattr(service, "build_candidate", fixed_candidate)

    ranked = service.rank(radars, limit=2)

    assert [item["spot_ticker"] for item in ranked] == ["WEAK_B", "WEAK_A"]


def test_historical_rank_tie_breaks_relative_strength_in_trade_direction():
    rows = [
        {
            "direction": "SHORT",
            "trend_state": "DOWNTREND",
            "trend_change_percent": 2.0,
            "relative_strength_available": True,
            "relative_strength_data": {"excess_change_percent": 1.0},
            "relative_strength": -1.0,
            "setup": "FIRST_REBOUND",
            "setup_state": "WATCH",
            "entry_trigger": 0.0,
            "average_daily_money": 300_000_000,
            "spot_ready_time": "08:30:00",
            "spot_ticker": "WEAK_A",
        },
        {
            "direction": "SHORT",
            "trend_state": "DOWNTREND",
            "trend_change_percent": 2.0,
            "relative_strength_available": True,
            "relative_strength_data": {"excess_change_percent": 1.0},
            "relative_strength": -3.0,
            "setup": "FIRST_REBOUND",
            "setup_state": "WATCH",
            "entry_trigger": 0.0,
            "average_daily_money": 300_000_000,
            "spot_ready_time": "08:30:00",
            "spot_ticker": "WEAK_B",
        },
    ]

    ranked = HistoricalCandidateRankerService.rank(rows, limit=2)

    assert [item["spot_ticker"] for item in ranked] == ["WEAK_B", "WEAK_A"]
