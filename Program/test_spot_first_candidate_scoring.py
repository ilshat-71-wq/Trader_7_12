from services.futures_trade_candidate_service import FuturesTradeCandidateService


def radar(ticker, setup_state, setup_quality):
    return {
        "status": "OK",
        "direction": "LONG",
        "futures_ticker": ticker,
        "futures_class_code": "SPBFUT",
        "futures_expiry": "2026-09-15",
        "spot_ticker": "BR" if ticker == "A1U6" else "NG",
        "spot_class_code": "SPBRU",
        "spot_type": "GOODS",
        "spot_name": "BRENT" if ticker == "A1U6" else "NATURAL GAS",
        "spot_price": 100,
        "radar_score": 80,
        "relative_strength": 0.5,
        "setup": "FIRST_PULLBACK",
        "setup_state": setup_state,
        "setup_quality_score": setup_quality,
        "setup_phase": "PULLBACK_CONSOLIDATION",
        "retracement_ratio": 0.5,
        "spot_money_volume": 200_000_000,
        "spot_money_ratio": 2.0,
        "spot_session_activity_ratio": 2.0,
        "average_daily_money": 300_000_000,
    }


def confirmation(ticker):
    return {
        "status": "OK",
        "direction": "LONG",
        "score": 80,
        "money_volume": 20_000_000,
        "trade_count": 100,
        "last_price": 100,
        "price_change_percent": 0.5,
        "futures_ticker": ticker,
        "futures_class_code": "SPBFUT",
    }


def test_confirmed_spot_setup_gets_quality_bonus():
    service = FuturesTradeCandidateService()
    watch = service.build_candidate(radar("A1U6", "WATCH", 75), confirmation("A1U6"))
    confirmed = service.build_candidate(radar("B1U6", "CONFIRMED", 75), confirmation("B1U6"))
    assert confirmed["candidate_score"] > watch["candidate_score"]


def run_tests():
    test_confirmed_spot_setup_gets_quality_bonus()
    print("PASS test_confirmed_spot_setup_gets_quality_bonus")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run_tests()
