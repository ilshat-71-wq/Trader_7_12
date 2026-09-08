from services.futures_oi_scanner_service import FuturesOIScannerService
from services.open_interest_service import OpenInterestService


class FakeAPI:
    access_token = "token"

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        assert instrument_type == "FUTURES"
        return [
            {
                "ticker": "AFLT-9.26",
                "underlyingAsset": "AFLT",
                "classCode": "SPBFUT",
            },
            {
                "ticker": "ALRS-9.26",
                "underlyingAsset": "ALRS",
                "classCode": "SPBFUT",
            },
            {
                "ticker": "APPF",
                "underlyingAsset": "APPF",
                "classCode": "SPBFUT",
            },
        ]

    def get_instruments_by_tickers(self, tickers):
        return []


def test_moex_short_code_mapping_for_standard_stock_futures():
    assert FuturesOIScannerService._oi_root(
        {"underlyingAsset": "AFLT"}, "AFLT-9.26", "AFLT"
    ) == "AF"
    assert FuturesOIScannerService._oi_root(
        {"underlyingAsset": "ALRS"}, "ALRS-9.26", "ALRS"
    ) == "AL"


def test_metadata_short_code_has_priority():
    row = {
        "underlyingAsset": "AFLT",
        "shortCode": "ZZ",
    }
    assert FuturesOIScannerService._oi_root(row, "AFLT-9.26", "AFLT") == "ZZ"


def test_active_contracts_group_by_oi_root_not_underlying_ticker():
    service = FuturesOIScannerService(api=FakeAPI(), oi_service=object())
    contracts = service._active_contracts()
    roots = {item["oi_root"] for item in contracts}
    assert roots == {"AF", "AL", "APPF"}
    assert len(contracts) == 3


def test_open_interest_aggregation_uses_both_sides():
    rows = [
        {"ticker": "AF", "pos": 100, "pos_long": 120, "pos_short": -80},
        {"ticker": "AF", "pos": -100, "pos_long": 80, "pos_short": -120},
    ]
    aggregate = OpenInterestService._aggregate_rows(rows)
    assert aggregate["oi_long"] == 200
    assert aggregate["oi_short"] == 200
    assert aggregate["oi"] == 200


def test_open_interest_http_error_is_not_silently_converted_to_empty_data():
    class ErrorResponse:
        def raise_for_status(self):
            raise RuntimeError("HTTP 403")

    def http_get(url, timeout=8):
        return ErrorResponse()

    service = OpenInterestService(http_get=http_get)
    try:
        service._request_all({"date": "2026-09-08"})
    except RuntimeError as exc:
        assert "HTTP 403" in str(exc)
    else:
        raise AssertionError("HTTP errors must propagate")
