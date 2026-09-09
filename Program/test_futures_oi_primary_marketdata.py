from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


class FakeAPI:
    access_token = "token"

    def authorize(self):
        return True

    def get_instruments(self, instrument_type):
        assert instrument_type == "FUTURES"
        return [
            {"ticker": "AFLT-9.26", "underlyingAsset": "AFLT", "classCode": "SPBFUT"},
            {"ticker": "ALRS-9.26", "underlyingAsset": "ALRS", "classCode": "SPBFUT"},
        ]

    def get_instruments_by_tickers(self, tickers):
        return []


class FakeOI:
    rows = {
        "AF": {
            "secid": "AFLT-9.26",
            "last": 100.0,
            "lasttoprevprice": 2.0,
            "openposition": 1200,
            "oichange": 100,
        },
        "AL": {
            "secid": "ALRS-9.26",
            "last": 50.0,
            "lasttoprevprice": -1.0,
            "openposition": 800,
            "oichange": -40,
        },
    }

    def _request_marketdata_family(self, root):
        return self.rows.get(root)

    def _marketdata_analysis(self, contract_ticker, root, price_change_percent, volume_percent):
        row = self.rows[root]
        oi = row["openposition"]
        oi_change = row["oichange"]
        return {
            "oi_status": "AVAILABLE",
            "oi_source": "MOEX_FUTURES_MARKETDATA",
            "oi_root": root,
            "oi_contract_ticker": row["secid"],
            "oi": oi,
            "oi_change_contracts": oi_change,
            "oi_change_percent": round(oi_change / (oi - oi_change) * 100.0, 3),
        }


def test_scan_uses_moex_marketdata_without_bcs_futures_quotes():
    service = FuturesOIMarketDataScannerService(api=FakeAPI(), oi_service=FakeOI())
    results, diagnostics = service.scan()

    assert len(results) == 2
    assert diagnostics["oi_source"] == "MOEX_FUTURES_MARKETDATA_PRIMARY"
    assert diagnostics["oi_available"] == 2
    assert {item["futures_ticker"] for item in results} == {"AFLT-9.26", "ALRS-9.26"}


def test_oi_change_is_separate_from_price_change():
    service = FuturesOIMarketDataScannerService(api=FakeAPI(), oi_service=FakeOI())
    results, _ = service.scan()
    by_root = {item["oi_root"]: item for item in results}

    assert by_root["AF"]["change_percent"] == 2.0
    assert by_root["AF"]["oi_analysis"]["oi_change_contracts"] == 100
    assert by_root["AL"]["change_percent"] == -1.0
    assert by_root["AL"]["oi_analysis"]["oi_change_contracts"] == -40
