from services.futures_oi_marketdata_scanner_service import FuturesOIMarketDataScannerService


class FakeBCS:
    def __init__(self, records):
        self.records = records

    def get_instruments_by_tickers(self, tickers):
        wanted = {str(ticker).upper() for ticker in tickers}
        return [record for record in self.records if str(record.get("ticker", "")).upper() in wanted]

    def get_quotes_batch(self, instruments):
        return [
            {"ticker": item["ticker"], "lastPrice": 100.0}
            for item in instruments
        ]


def make_scanner(records):
    scanner = object.__new__(FuturesOIMarketDataScannerService)
    scanner.api = FakeBCS(records)
    scanner._underlying_class_codes = {}
    scanner._underlying_family_tickers = {}
    scanner._underlying_bcs_tickers = {}
    scanner._underlying_mapping_source = {}
    scanner._underlying_day_change_cache = {}
    return scanner


def test_moex_display_name_does_not_override_canonical_gazp_mapping():
    scanner = make_scanner([
        {"ticker": "GAZP", "classCode": "TQBR", "instrumentType": "STOCK"},
    ])

    quotes = scanner._underlying_quotes([
        {"oi_root": "GZ", "underlying_ticker": "ГАЗПРОМ"},
    ])

    assert scanner._underlying_family_tickers["GZ"] == "GAZP"
    assert scanner._underlying_bcs_tickers["GAZP"] == "GAZP"
    assert scanner._underlying_class_codes["GAZP"] == "TQBR"
    assert "GAZP" in quotes


def test_rts_and_cny_use_canonical_underlyings_not_raw_display_text():
    scanner = make_scanner([
        {"ticker": "RTS", "classCode": "RTSI", "instrumentType": "INDICES"},
        {"ticker": "CNYRUB_TOM", "classCode": "CETS", "instrumentType": "CURRENCY"},
    ])

    scanner._underlying_quotes([
        {"oi_root": "RI", "underlying_ticker": "ИНДЕКС РТС"},
        {"oi_root": "CNY", "underlying_ticker": "CNY"},
    ])

    assert scanner._underlying_family_tickers["RI"] == "RTS"
    assert scanner._underlying_family_tickers["CNY"] == "CNYRUB"
    assert scanner._underlying_bcs_tickers["RTS"] == "RTS"
    assert scanner._underlying_bcs_tickers["CNYRUB"] == "CNYRUB_TOM"


def test_moex_index_futures_share_real_imoex_underlying():
    scanner = make_scanner([
        {"ticker": "IMOEX", "classCode": "INDX", "instrumentType": "INDICES"},
    ])

    scanner._underlying_quotes([
        {"oi_root": "MX", "underlying_ticker": "ИНДЕКС МОСБИРЖИ"},
        {"oi_root": "MM", "underlying_ticker": "ИНДЕКС IMOEX МИНИ"},
        {"oi_root": "IMOEXF", "underlying_ticker": "IMOEXF"},
    ])

    assert scanner._underlying_family_tickers["MX"] == "IMOEX"
    assert scanner._underlying_family_tickers["MM"] == "IMOEX"
    assert scanner._underlying_family_tickers["IMOEXF"] == "IMOEX"
    assert scanner._underlying_class_codes["IMOEX"] == "INDX"
    assert scanner._underlying_bcs_tickers["IMOEX"] == "IMOEX"


def test_currency_futures_keep_canonical_bcs_underlying_mapping():
    scanner = make_scanner([
        {"ticker": "USDRUB_TOM", "classCode": "CETS", "instrumentType": "CURRENCY"},
        {"ticker": "EURRUB_TOM", "classCode": "CETS", "instrumentType": "CURRENCY"},
        {"ticker": "CNYRUB_TOM", "classCode": "CETS", "instrumentType": "CURRENCY"},
        {"ticker": "GLDRUB_TOM", "classCode": "CETS_MTL", "instrumentType": "GOODS"},
    ])

    scanner._underlying_quotes([
        {"oi_root": "SI", "underlying_ticker": "USDRUB"},
        {"oi_root": "EU", "underlying_ticker": "EURRUB"},
        {"oi_root": "CR", "underlying_ticker": "CNYRUB"},
        {"oi_root": "GD", "underlying_ticker": "GLDRUB_TOM"},
    ])

    assert scanner._underlying_family_tickers["SI"] == "USDRUB"
    assert scanner._underlying_family_tickers["EU"] == "EURRUB"
    assert scanner._underlying_family_tickers["CR"] == "CNYRUB"
    assert scanner._underlying_family_tickers["GD"] == "GLDRUB_TOM"
    assert scanner._underlying_bcs_tickers["USDRUB"] == "USDRUB_TOM"
    assert scanner._underlying_bcs_tickers["EURRUB"] == "EURRUB_TOM"
    assert scanner._underlying_bcs_tickers["CNYRUB"] == "CNYRUB_TOM"
    assert scanner._underlying_bcs_tickers["GLDRUB_TOM"] == "GLDRUB_TOM"
