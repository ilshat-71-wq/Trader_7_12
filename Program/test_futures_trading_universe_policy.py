from services.futures_trading_universe_policy import FuturesTradingUniversePolicy


def test_allows_dated_russian_stock_future():
    assert FuturesTradingUniversePolicy.is_allowed("SRU6", "SR", "SBER")
    assert FuturesTradingUniversePolicy.reason("SRU6", "SR", "SBER") == "APPROVED_RUSSIAN_STOCK"


def test_allows_dated_currency_and_commodity_futures():
    for ticker, root in (
        ("SIU6", "SI"),
        ("EUU6", "EU"),
        ("CRU6", "CR"),
        ("BRV6", "BR"),
        ("CLU6", "CL"),
        ("NGU6", "NG"),
        ("GDU6", "GD"),
        ("GLU6", "GL"),
    ):
        assert FuturesTradingUniversePolicy.is_allowed(ticker, root, "")


def test_rejects_perpetual_and_auto_roll_products():
    for ticker, root, underlying in (
        ("USDRUBF", "USDRUBF", "USDRUB"),
        ("GAZPF", "GAZPF", "GAZP"),
        ("SBERF", "SBERF", "SBER"),
    ):
        assert not FuturesTradingUniversePolicy.is_allowed(ticker, root, underlying)
        assert FuturesTradingUniversePolicy.reason(ticker, root, underlying) == "PERPETUAL_OR_AUTO_ROLL"


def test_rejects_crypto_foreign_and_index_futures():
    assert not FuturesTradingUniversePolicy.is_allowed("BTCU6", "BT", "BTC")
    assert not FuturesTradingUniversePolicy.is_allowed("APPFU6", "APPF", "APPF")
    assert not FuturesTradingUniversePolicy.is_allowed("MXU6", "MX", "IMOEX")
    assert not FuturesTradingUniversePolicy.is_allowed("RIU6", "RI", "RTS")


def test_unknown_new_product_does_not_enter_automatically():
    assert not FuturesTradingUniversePolicy.is_allowed("NEWAU6", "NEW", "NEWCO")


def test_non_dated_contract_is_rejected_even_for_allowed_root():
    assert not FuturesTradingUniversePolicy.is_allowed("SI", "SI", "USDRUB")
