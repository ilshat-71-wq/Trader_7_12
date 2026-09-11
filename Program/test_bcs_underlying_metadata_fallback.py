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
