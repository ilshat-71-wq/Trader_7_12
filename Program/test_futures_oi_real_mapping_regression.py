from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


class FakeBCS:
    def get_instruments_by_tickers(self, tickers):
        records = {
            "SBER": {"ticker": "SBER", "boards": [{"classCode": "TQBR", "exchange": "MOEX"}]},
            "LKOH": {"ticker": "LKOH", "boards": [{"classCode": "TQBR", "exchange": "MOEX"}]},
            "GLDRUB_TOM": {"ticker": "GLDRUB_TOM", "shortName": "Золото", "boards": [{"classCode": "CETS_MTL", "exchange": "MOEX"}]},
            "USDRUB": {"ticker": "USDRUB_TOM", "boards": [{"classCode": "CETS", "exchange": "MOEX"}]},
            "EURRUB": {"ticker": "EUR_RUB__TOM", "boards": [{"classCode": "CETS", "exchange": "MOEX"}]},
            "CNYRUB": {"ticker": "CNYRUB_TOM", "boards": [{"classCode": "CETS", "exchange": "MOEX"}]},
        }
        return [records[ticker] for ticker in tickers if ticker in records]

    def get_quotes_batch(self, instruments):
        return [{"ticker": item["ticker"], "lastPrice": 1.0} for item in instruments]


def make_service():
    service = object.__new__(FuturesOIMarketDataScannerService)
    service.api = FakeBCS()
    return service


def test_real_family_to_bcs_mapping():
    service = make_service()
    contracts = [
        {"oi_root": "SR", "underlying_ticker": "СБЕРБАНК"},
        {"oi_root": "LK", "underlying_ticker": "ЛУКОЙЛ"},
        {"oi_root": "GD", "underlying_ticker": "ЗОЛОТО РАСЧЕТНЫЙ"},
        {"oi_root": "SI", "underlying_ticker": "USD/RUB"},
        {"oi_root": "EU", "underlying_ticker": "EUR/RUB"},
        {"oi_root": "CR", "underlying_ticker": "CNY/RUB"},
    ]

    quotes = service._underlying_quotes(contracts)

    assert service._underlying_family_tickers == {
        "SR": "SBER",
        "LK": "LKOH",
        "GD": "GLDRUB_TOM",
        "SI": "USDRUB",
        "EU": "EURRUB",
        "CR": "CNYRUB",
    }
    assert service._underlying_bcs_tickers == {
        "SBER": "SBER",
        "LKOH": "LKOH",
        "GLDRUB_TOM": "GLDRUB_TOM",
        "USDRUB": "USDRUB_TOM",
        "EURRUB": "EUR_RUB__TOM",
        "CNYRUB": "CNYRUB_TOM",
    }
    assert service._underlying_class_codes == {
        "SBER": "TQBR",
        "LKOH": "TQBR",
        "GLDRUB_TOM": "CETS_MTL",
        "USDRUB": "CETS",
        "EURRUB": "CETS",
        "CNYRUB": "CETS",
    }
    assert set(quotes) == {
        "SBER",
        "LKOH",
        "GLDRUB_TOM",
        "USDRUB_TOM",
        "EUR_RUB__TOM",
        "CNYRUB_TOM",
    }


def test_unverified_oil_and_gas_are_not_replaced():
    assert FuturesOIMarketDataScannerService._family_to_underlying("BR") == "BR"
    assert FuturesOIMarketDataScannerService._family_to_underlying("NG") == "NG"


def test_gold_semantic_aliases_do_not_prefer_etf_symbol():
    aliases = FuturesOIMarketDataScannerService._semantic_aliases("GLDRUB_TOM")
    assert "GLDRUBTOM" in aliases
    assert "GLDRUB" in aliases
    assert "GOLD" not in aliases
