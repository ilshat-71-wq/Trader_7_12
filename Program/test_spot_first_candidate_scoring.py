from services.futures_trade_candidate_service import FuturesTradeCandidateService


def radar(ticker, setup_state, setup_quality):
    return {
        "status": "OK", "direction": "LONG", "spot_group": "OIL",
        "futures_ticker": ticker, "futures_class_code": "SPBFUT", "futures_expiry": "2026-09-15",
        "spot_ticker": "BR" if ticker == "A1U6" else "NG", "spot_class_code": "SPOT", "spot_type": "GOODS",
        "spot_name": "BRENT" if ticker == "A1U6" else "NATURAL GAS", "spot_price": 100, "radar_score": 80,
        "relative_strength": 0.5, "relative_strength_status": "OK", "setup": "FIRST_PULLBACK",
        "setup_direction": "LONG", "setup_state": setup_state, "setup_quality_score": setup_quality,
        "setup_phase": "PULLBACK_CONSOLIDATION", "retracement_ratio": 0.5,
        "spot_money_volume": 200_000_000, "spot_money_ratio": 2.0, "spot_session_activity_ratio": 2.0,
        "average_daily_money": 300_000_000,
    }


def test_setup_state_is_not_an_opportunity_score_gate():
    watch = FuturesTradeCandidateService.build_candidate(radar("A1U6", "WATCH", 75))
    confirmed = FuturesTradeCandidateService.build_candidate(radar("B1U6", "CONFIRMED", 75))
    assert watch is not None and confirmed is not None
    assert watch["setup_state"] == "WATCH"
    assert confirmed["setup_state"] == "CONFIRMED"
    assert confirmed["candidate_score"] == watch["candidate_score"]
