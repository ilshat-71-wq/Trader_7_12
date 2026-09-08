from services.futures_oi_scanner_service import FuturesOIScannerService


class FakeAPI:
    access_token = "token"

    def authorize(self):
        return True

    def get_instruments(self, instrument_type="FUTURES"):
        assert instrument_type == "FUTURES"
        return [
            {
                "ticker": "SBER-12.26",
                "type": "FUTURES",
                "underlyingTicker": "SBER",
            }
        ]

    def get_instruments_by_tickers(self, tickers):
        return [
            {
                "ticker": ticker,
                "expirationDate": "2099-12-18",
            }
            for ticker in tickers
        ]

    def get_quotes_batch(self, instruments):
        return []


def test_futures_classcode_fallback_keeps_contract_quoteable():
    service = FuturesOIScannerService(api=FakeAPI(), oi_service=object())

    contracts = service._active_contracts()

    assert len(contracts) == 1
    assert contracts[0]["futures_class_code"] == "SPBFUT"
    assert service._last_contract_diagnostics["class_code_available"] == 0
    assert service._last_contract_diagnostics["class_code_fallback"] == 1
