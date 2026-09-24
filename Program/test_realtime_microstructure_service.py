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


def test_subscription_success_is_counted_per_instrument():
    worker = RealtimeMicrostructureWorker(
        None,
        [
            {"ticker": "SBER", "classCode": "TQBR"},
            {"ticker": "GAZP", "classCode": "TQBR"},
        ],
    )
    worker._subscription_requested = {0: True, 2: True}
    worker._handle({
        "responseType": "OrderBookSuccess",
        "subscribeType": 0,
        "ticker": "SBER",
        "classCode": "TQBR",
    })
    worker._handle({
        "responseType": "LastTradesSuccess",
        "subscribeType": 0,
        "ticker": "SBER",
        "classCode": "TQBR",
    })
    diagnostics = worker._realtime_diagnostics()
    assert diagnostics["orderbook_accepted"] == 1
    assert diagnostics["lasttrades_accepted"] == 1
    assert diagnostics["orderbook_messages"] == 0
    assert diagnostics["lasttrades_messages"] == 0


def test_subscription_error_is_visible_in_diagnostics():
    worker = RealtimeMicrostructureWorker(
        None,
        [{"ticker": "BAD", "classCode": "SPBFUT"}],
    )
    worker._handle({
        "responseType": "OrderBook",
        "errors": [{"code": "NOT_FOUND", "message": "instrument not found"}],
    })
    diagnostics = worker._realtime_diagnostics()
    assert diagnostics["subscription_errors"] == ["NOT_FOUND: instrument not found"]
    assert diagnostics["last_error"] == "NOT_FOUND: instrument not found"


def test_market_data_messages_are_counted():
    worker = RealtimeMicrostructureWorker(
        None,
        [{"ticker": "SBER", "classCode": "TQBR"}],
    )
    worker._handle({
        "responseType": "OrderBook",
        "ticker": "SBER",
        "classCode": "TQBR",
        "bidVolume": 80,
        "askVolume": 20,
        "bids": [{"price": 100, "quantity": 80}],
        "asks": [{"price": 101, "quantity": 20}],
    })
    worker._handle({
        "responseType": "LastTrades",
        "ticker": "SBER",
        "classCode": "TQBR",
        "side": "BUY",
        "price": 100,
        "quantity": 10,
    })
    diagnostics = worker._realtime_diagnostics()
    assert diagnostics["orderbook_messages"] == 1
    assert diagnostics["lasttrades_messages"] == 1


def test_connection_error_is_preserved_in_realtime_diagnostics():
    worker = RealtimeMicrostructureWorker(
        None,
        [{"ticker": "ONZ6", "classCode": "SPBFUT"}],
    )
    worker._last_error = "WebSocketProxyException: proxy connection failed"
    diagnostics = worker._realtime_diagnostics()
    assert diagnostics["last_error"] == "WebSocketProxyException: proxy connection failed"

def test_subscription_timeout_diagnostic_contains_partial_ack_counts():
    worker = RealtimeMicrostructureWorker(
        None,
        [
            {"ticker": "ONZ6", "classCode": "SPBFUT"},
            {"ticker": "SBER", "classCode": "TQBR"},
        ],
    )
    worker._subscription_accepted = {
        0: {("ONZ6", "SPBFUT")},
        2: set(),
    }
    expected = {(item["ticker"], item["classCode"]) for item in worker.instruments}
    worker._last_error = (
        "BCS subscription acknowledgement timeout: "
        f"BOOK {len(worker._subscription_accepted[0])}/{len(expected)}, "
        f"TAPE {len(worker._subscription_accepted[2])}/{len(expected)}"
    )
    assert worker._last_error == "BCS subscription acknowledgement timeout: BOOK 1/2, TAPE 0/2"
