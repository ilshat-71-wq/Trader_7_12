from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


def test_session_turnover_uses_valtoday_only():
    marketdata = {"valtoday": "123456789", "volume": 999999}
    assert FuturesOIMarketDataScannerService._session_turnover(marketdata) == 123456789.0
    assert FuturesOIMarketDataScannerService._session_turnover_source(marketdata) == "VALTODAY"


def test_session_turnover_does_not_fallback_to_synthetic_or_ambiguous_value():
    marketdata = {"value": 123456789, "volume": 1000}
    assert FuturesOIMarketDataScannerService._session_turnover(marketdata) == 0.0
    assert FuturesOIMarketDataScannerService._session_turnover_source(marketdata) == "UNAVAILABLE"


def test_underlying_change_prefers_direct_bcs_percent():
    change, source = FuturesOIMarketDataScannerService._underlying_change_percent({
        "lastPrice": 101.0,
        "openPrice": 100.0,
        "changePercent": 1.7,
    })
    assert change == 1.7
    assert source == "changePercent"


def test_underlying_change_falls_back_to_last_vs_previous():
    change, source = FuturesOIMarketDataScannerService._underlying_change_percent({
        "lastPrice": 101.0,
        "prevClose": 100.0,
    })
    assert change == 1.0
    assert source == "LAST_VS_PREVIOUS"
