from api.bcs_api import BCSAPI


class FakeBCS(BCSAPI):
    def __init__(self):
        pass

    def get_instruments(self, instrument_type="FUTURES"):
        data = {
            "CURRENCY": [
                {"ticker": "USDRUB_TOM", "classCode": "CETS"},
                {"ticker": "EURRUB_TOM", "classCode": "CETS"},
                {"ticker": "CNYRUB_TOM", "classCode": "CETS"},
            ],
            "STOCK": [
                {"ticker": "SBER", "classCode": "TQBR"},
                {"ticker": "GAZP", "classCode": "TQBR"},
            ],
            "FOREIGN_STOCK": [],
            "ETF": [],
            "GOODS": [],
            "INDICES": [
                {"ticker": "IMOEX", "classCode": "TQBR"},
            ],
        }
        return data[instrument_type]


def test_real_underlying_fallback_uses_non_futures_by_type_metadata():
    api = FakeBCS()
    existing = [
        {"ticker": "SBER"},
        {"ticker": "USDRUB"},
    ]

    records, diagnostics = api._underlying_metadata_fallback(
        ["SBER", "USDRUB"], existing
    )

    resolved = {
        record["ticker"]: record.get("classCode")
        for record in records
        if isinstance(record, dict) and record.get("classCode")
    }

    assert resolved["SBER"] == "TQBR"
    assert resolved["USDRUB_TOM"] == "CETS"
    assert diagnostics["fallback_matches"] == 2
    assert diagnostics["fallback_unresolved"] == 0


def test_lookup_key_handles_real_currency_ticker_variants():
    assert BCSAPI._instrument_lookup_key("USDRUB") == "USDRUB"
    assert BCSAPI._instrument_lookup_key("USDRUB_TOM") == "USDRUB"
    assert BCSAPI._instrument_lookup_key("USD/RUB") == "USDRUB"
    assert BCSAPI._instrument_lookup_key("USDRUBF") == "USDRUB"


def test_fallback_canonicalizes_requested_currency_alias_before_directory_match():
    api = FakeBCS()
    records, diagnostics = api._underlying_metadata_fallback(["USDRUB_TOM"], [])
    resolved = {record["ticker"]: record.get("classCode") for record in records if isinstance(record, dict) and record.get("classCode")}
    assert resolved["USDRUB_TOM"] == "CETS"
    assert diagnostics["fallback_unresolved"] == 0



def test_futures_card_base_asset_reference_prefers_real_bcs_metadata():
    from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
    record = {"ticker": "NGU6", "instrumentType": "FUTURES", "baseAssetTicker": "NG", "baseAssetClassCode": "SPBFUT"}
    resolved = FuturesOIMarketDataScannerService._base_asset_reference(record)
    assert resolved == {"ticker": "NG", "classCode": "SPBFUT", "source": "futures_card"}


def test_futures_card_nested_base_asset_is_supported():
    from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService
    record = {"ticker": "SIZ6", "instrumentType": "FUTURES", "baseAsset": {"ticker": "USDRUB_TOM", "classCode": "CETS"}}
    resolved = FuturesOIMarketDataScannerService._base_asset_reference(record)
    assert resolved["ticker"] == "USDRUB_TOM"
    assert resolved["classCode"] == "CETS"


def test_get_instruments_by_tickers_reuses_overlapping_ticker_cards(monkeypatch):
    from types import SimpleNamespace
    from api.request_helper import RequestHelper

    class FakeTickerBCS(BCSAPI):
        def __init__(self):
            self._ticker_metadata_cache = {}
            self._ticker_metadata_record_cache = {}
            self._underlying_metadata_index_cache = {}
            self.info_url = "https://test.local"
            self.INSTRUMENT_METADATA_CACHE_TTL = 300.0

        def headers(self):
            return {}

    api = FakeTickerBCS()
    calls = []

    def fake_post(url, headers=None, json=None, **kwargs):
        calls.append(list(json["tickers"]))
        records = [{"ticker": ticker, "classCode": "TQBR"} for ticker in json["tickers"]]
        return SimpleNamespace(status_code=200, text="", json=lambda: {"instruments": records})

    monkeypatch.setattr(RequestHelper, "post", fake_post)

    first = api.get_instruments_by_tickers(["SBER", "GAZP"], resolve_underlying=False)
    second = api.get_instruments_by_tickers(["GAZP", "LKOH"], resolve_underlying=False)

    assert {record["ticker"] for record in first} == {"SBER", "GAZP"}
    assert {record["ticker"] for record in second} == {"GAZP", "LKOH"}
    assert calls == [["GAZP", "SBER"], ["LKOH"]]



def test_get_instruments_by_tickers_reuses_shared_catalog(monkeypatch):
    from types import SimpleNamespace
    from api.request_helper import RequestHelper
    from services.bcs_metadata_cache_service import BCSMetadataCacheService

    class FakeTickerBCS(BCSAPI):
        def __init__(self):
            self._ticker_metadata_cache = {}
            self._ticker_metadata_record_cache = {}
            self._underlying_metadata_index_cache = {}
            self.info_url = "https://test.local"
            self.INSTRUMENT_METADATA_CACHE_TTL = 300.0

        def headers(self):
            return {}

    BCSMetadataCacheService.clear()
    try:
        now = __import__("time").monotonic()
        with BCSMetadataCacheService._lock:
            BCSMetadataCacheService._by_type["STOCK"] = {
                "at": now,
                "records": [
                    {"ticker": "SBER", "classCode": "TQBR"},
                    {"ticker": "GAZP", "classCode": "TQBR"},
                ],
            }

        api = FakeTickerBCS()
        calls = []

        def fake_post(url, headers=None, json=None, **kwargs):
            calls.append(list(json["tickers"]))
            records = [{"ticker": ticker, "classCode": "TQBR"} for ticker in json["tickers"]]
            return SimpleNamespace(status_code=200, text="", json=lambda: {"instruments": records})

        monkeypatch.setattr(RequestHelper, "post", fake_post)

        records = api.get_instruments_by_tickers(["SBER", "GAZP"], resolve_underlying=False)

        assert {record["ticker"] for record in records} == {"SBER", "GAZP"}
        assert calls == []
    finally:
        BCSMetadataCacheService.clear()
