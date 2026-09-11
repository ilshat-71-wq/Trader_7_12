from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


def test_missing_underlying_is_not_available():
    service = FuturesOIMarketDataScannerService(api=object(), oi_service=object())
    service._underlying_class_codes = {}
    assert service._underlying_day_change("UNKNOWN") == (None, "NO_CLASS_CODE")


def test_missing_base_data_cannot_be_reported_as_available():
    service = FuturesOIMarketDataScannerService(api=object(), oi_service=object())
    service._underlying_class_codes = {}
    value, source = service._underlying_day_change("SBER")
    assert value is None
    assert source == "NO_CLASS_CODE"
