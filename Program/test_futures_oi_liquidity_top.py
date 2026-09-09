from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


def test_session_turnover_uses_exchange_money_not_synthetic_volume():
    assert FuturesOIMarketDataScannerService._session_turnover({"valtoday": "125000000"}) == 125000000
    assert FuturesOIMarketDataScannerService._session_turnover({"voltoday": 100000, "last": 1000}) == 0


def test_liquidity_top_ranks_current_session_money_first():
    service = FuturesOIMarketDataScannerService.__new__(FuturesOIMarketDataScannerService)
    service.LIQUIDITY_TOP_LIMIT = 2
    rows = [
        {"session_turnover_rub": 50_000_000, "liquidity_score": 1, "oi_analysis": {"oi": 100}},
        {"session_turnover_rub": 200_000_000, "liquidity_score": 1, "oi_analysis": {"oi": 100}},
        {"session_turnover_rub": 90_000_000, "liquidity_score": 1, "oi_analysis": {"oi": 100}},
    ]
    rows.sort(key=lambda x: (x["session_turnover_rub"], x["liquidity_score"], x["oi_analysis"]["oi"]), reverse=True)
    selected = rows[: service.LIQUIDITY_TOP_LIMIT]
    assert [row["session_turnover_rub"] for row in selected] == [200_000_000, 90_000_000]
