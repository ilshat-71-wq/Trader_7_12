from api.bcs_underlying_catalog import (
    BCS_UNDERLYING_INSTRUMENTS,
    CANONICAL_FUTURES_UNDERLYINGS,
    preferred_instruments,
)


def test_bcs_currency_and_gold_instruments_are_exact():
    assert preferred_instruments("USDRUB")[0] == {"ticker": "USDRUB_TOM", "classCode": "CETS"}
    assert preferred_instruments("EURRUB")[0] == {"ticker": "EURRUB_TOM", "classCode": "CETS"}
    assert preferred_instruments("CNYRUB")[0] == {"ticker": "CNYRUB_TOM", "classCode": "CETS"}
    assert preferred_instruments("GLDRUB_TOM")[0] == {"ticker": "GLDRUB_TOM", "classCode": "CETS_MTL"}


def test_bcs_index_and_equity_classes_are_exact():
    assert preferred_instruments("IMOEX")[0] == {"ticker": "IMOEX", "classCode": "INDX"}
    assert preferred_instruments("RTS")[0] == {"ticker": "RTS", "classCode": "INDX"}
    assert preferred_instruments("RGBI")[0] == {"ticker": "RGBI", "classCode": "INDX"}
    assert preferred_instruments("SBER")[0] == {"ticker": "SBER", "classCode": "TQBR"}
    assert preferred_instruments("GAZP")[0] == {"ticker": "GAZP", "classCode": "SMAL"}


def test_bcs_foreign_etf_classes_are_exact():
    assert preferred_instruments("QQQ")[0] == {"ticker": "QQQ", "classCode": "SPBXM"}
    assert preferred_instruments("SPY")[0] == {"ticker": "SPY", "classCode": "QMEBLCK"}


def test_futures_families_resolve_to_canonical_underlyings():
    assert CANONICAL_FUTURES_UNDERLYINGS["SI"] == "USDRUB"
    assert CANONICAL_FUTURES_UNDERLYINGS["CR"] == "CNYRUB"
    assert CANONICAL_FUTURES_UNDERLYINGS["CNY"] == "CNYRUB"
    assert CANONICAL_FUTURES_UNDERLYINGS["GD"] == "GLDRUB_TOM"
    assert CANONICAL_FUTURES_UNDERLYINGS["MX"] == "IMOEX"
    assert CANONICAL_FUTURES_UNDERLYINGS["MM"] == "IMOEX"
    assert CANONICAL_FUTURES_UNDERLYINGS["IMOEXF"] == "IMOEX"


def test_catalog_has_no_derivative_instruments():
    for records in BCS_UNDERLYING_INSTRUMENTS.values():
        for record in records:
            assert not record["ticker"].endswith("F")
