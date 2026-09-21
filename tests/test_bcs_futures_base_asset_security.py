from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


def test_bcs_futures_card_uses_base_asset_security_fields():
    record = {
        "ticker": "NGU6",
        "instrumentType": "FUTURES",
        "baseAsset": "Природный газ",
        "baseAssetSecurityClassCode": "FEG",
        "baseAssetSecuritySecCode": "NGas1026",
    }

    assert FuturesOIMarketDataScannerService._base_asset_reference(record) == {
        "ticker": "NGAS1026",
        "classCode": "FEG",
        "source": "futures_card_base_asset_security",
    }


def test_bcs_usd_base_reference_is_real_currency_not_perpetual_future():
    record = {
        "ticker": "USDRUBF",
        "instrumentType": "FUTURES",
        "baseAsset": "USD/RUB вечный",
        "baseAssetSecurityClassCode": "CETS_FX",
        "baseAssetSecuritySecCode": "USD000SMALL",
    }

    base = FuturesOIMarketDataScannerService._base_asset_reference(record)

    assert base["ticker"] == "USD000SMALL"
    assert base["classCode"] == "CETS_FX"
    assert base["source"] == "futures_card_base_asset_security"


def test_missing_authoritative_security_fields_stays_on_existing_metadata_path():
    record = {
        "ticker": "NGU6",
        "instrumentType": "FUTURES",
        "baseAsset": "Природный газ",
    }

    assert FuturesOIMarketDataScannerService._base_asset_reference(record) is None

def test_futures_base_metadata_uses_complete_bcs_futures_directory_when_direct_lookup_is_empty(monkeypatch):
    scanner = FuturesOIMarketDataScannerService()

    monkeypatch.setattr(
        scanner.api,
        "get_instruments_by_tickers",
        lambda tickers, resolve_underlying=False: [],
    )
    monkeypatch.setattr(
        scanner.api,
        "get_instruments",
        lambda instrument_type="FUTURES": [
            {
                "ticker": "SIZ6",
                "instrumentType": "FUTURES",
                "baseAsset": "USD/RUB",
                "baseAssetSecurityClassCode": "CETS_FX",
                "baseAssetSecuritySecCode": "USD000SMALL",
            }
        ],
    )

    resolved, diagnostics = scanner._futures_base_asset_metadata(
        [{"oi_root": "SI", "futures_ticker": "SIZ6"}]
    )

    assert resolved["SI"] == {
        "ticker": "USD000SMALL",
        "classCode": "CETS_FX",
        "source": "futures_card_base_asset_security",
    }
    assert diagnostics["futures_base_metadata_directory_fallback"] == 1
