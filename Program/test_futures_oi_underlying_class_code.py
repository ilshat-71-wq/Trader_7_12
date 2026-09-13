import services.futures_oi_marketdata_scanner_service as scanner_module
from services.futures_oi_marketdata_scanner_service import (
    FuturesOIMarketDataScannerService,
)


class FakeOI:
    TIMEOUT = 15
    MARKETDATA_RETRIES = 3


class FakeAPI:
    access_token = "test"

    def __init__(self):
        self.quote_requests = []

    def get_instruments_by_tickers(self, tickers):
        return [{
            "ticker": "SBER",
            "_underlying_bcs_class_code": "TQBR",
            "_underlying_bcs_ticker": "SBER",
            "_underlying_mapping_source": "BCS_BY_TYPE_METADATA",
        }]

    def get_quotes_batch(self, instruments):
        self.quote_requests.append(list(instruments))
        return [{
            "ticker": "SBER",
            "lastPrice": 100.0,
        }]


def test_underlying_fallback_class_code_reaches_quote_request(monkeypatch):
    monkeypatch.setattr(scanner_module, "preferred_instruments", lambda ticker: ())

    api = FakeAPI()
    scanner = FuturesOIMarketDataScannerService(
        api=api,
        oi_service=FakeOI(),
    )

    quotes = scanner._underlying_quotes([
        {
            "oi_root": "SR",
            "underlying_class_code": "",
        }
    ])

    assert scanner._underlying_class_codes["SBER"] == "TQBR"
    assert scanner._underlying_bcs_tickers["SBER"] == "SBER"
    assert api.quote_requests == [
        [{"ticker": "SBER", "classCode": "TQBR"}]
    ]
    assert "SBER" in quotes
