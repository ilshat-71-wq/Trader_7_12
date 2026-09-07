from services.futures_oi_scanner_service import FuturesOIScannerService


class FakeOI:
    def analyze(self, root, price_change_percent, volume_percent=None, as_of=None):
        return {
            "oi_status": "AVAILABLE",
            "oi_root": root,
            "oi": 100000.0,
            "oi_change_percent": 2.5,
            "oi_zscore": 2.1,
            "oi_regime": "NEW_POSITION_BUILDING_UP",
            "oi_strength": "STRONG",
        }


class FakeAPI:
    access_token = "ok"

    def authorize(self):
        return True

    def get_instruments(self, kind):
        assert kind == "FUTURES"
        return [
            {
                "ticker": "Si-9.26",
                "classCode": "SPBFUT",
                "underlyingAsset": "USDRUB_TOM",
                "underlyingTicker": "USDRUB_TOM",
                "underlyingClassCode": "CETS",
                "expirationDate": "2099-09-01",
            },
            {
                "ticker": "Si-12.26",
                "classCode": "SPBFUT",
                "underlyingAsset": "USDRUB_TOM",
                "underlyingTicker": "USDRUB_TOM",
                "underlyingClassCode": "CETS",
                "expirationDate": "2099-12-01",
            },
            {
                "ticker": "BR-10.26",
                "classCode": "SPBFUT",
                "underlyingAsset": "BR",
                "underlyingTicker": "BR",
                "underlyingClassCode": "SPBFUT",
                "expirationDate": "2099-10-01",
            },
        ]

    def get_quotes_batch(self, instruments):
        result = []
        for instrument in instruments:
            ticker = instrument["ticker"]
            if ticker == "Si-9.26":
                result.append({"ticker": ticker, "lastPrice": 87000, "openPrice": 86000, "volume": 1000})
            elif ticker == "BR-10.26":
                result.append({"ticker": ticker, "lastPrice": 80, "openPrice": 79, "volume": 500})
            elif ticker == "USDRUB_TOM":
                result.append({"ticker": ticker, "lastPrice": 86.7, "openPrice": 85.9})
            elif ticker == "BR":
                result.append({"ticker": ticker, "lastPrice": 80.5, "openPrice": 79.8})
        return result


def test_si_root_is_separate_from_underlying():
    service = FuturesOIScannerService(api=FakeAPI(), oi_service=FakeOI())
    contracts = service._active_contracts()
    si = next(x for x in contracts if x["futures_root"] == "SI")
    assert si["oi_root"] == "SI"
    assert si["underlying_asset"] == "USDRUB"
    assert si["futures_ticker"] == "Si-9.26"
    assert si["futures_ticker_normalized"] == "SI-9.26"
    assert si["curve_role"] == "FRONT"


def test_scan_exposes_underlying_and_oi_fields_for_all_roots():
    service = FuturesOIScannerService(api=FakeAPI(), oi_service=FakeOI())
    results, diagnostics = service.scan()
    assert diagnostics["status"] == "OK"
    roots = {row["futures_root"] for row in results}
    assert roots == {"SI", "BR"}
    si = next(row for row in results if row["futures_root"] == "SI")
    assert si["underlying_asset"] == "USDRUB"
    assert si["underlying_price"] == 86.7
    assert si["oi_analysis"]["oi_root"] == "SI"
    assert si["oi_analysis"]["oi_regime"] == "NEW_POSITION_BUILDING_UP"
