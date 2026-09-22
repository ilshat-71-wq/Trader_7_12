from services.realtime_microstructure_service import RealtimeMicrostructureWorker


def test_book_score_uses_real_bid_ask_imbalance():
    worker = RealtimeMicrostructureWorker(None, [])
    metrics = worker._book_metrics({
        "bidVolume": 80,
        "askVolume": 20,
        "bids": [{"price": 100, "quantity": 80}],
        "asks": [{"price": 101, "quantity": 20}],
    })
    assert metrics["book_imbalance_pct"] == 60.0
    assert metrics["book_score"] == 80.0
    assert metrics["book_levels"] == 1


def test_tape_score_is_neutral_for_equal_real_trade_flow():
    worker = RealtimeMicrostructureWorker(None, [])
    now = __import__("time").time()
    worker._trades["SBER"].extend([
        (now - 20, "BUY", 1000, None),
        (now - 10, "SELL", 1000, None),
    ])
    metrics = worker._tape_metrics("SBER")
    assert metrics["tape_delta_pct"] == 0.0
    assert metrics["tape_score"] == 50.0
    assert metrics["tape_trade_count"] == 2


def test_worker_limits_subscription_to_bcs_documented_maximum():
    instruments = [{"ticker": f"S{i}", "classCode": "TQBR"} for i in range(150)]
    worker = RealtimeMicrostructureWorker(None, instruments)
    assert len(worker.instruments) == 100
