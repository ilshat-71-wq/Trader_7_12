from api.bcs_underlying_catalog import preferred_instruments


def test_usdrub_prefers_verified_bcs_base_spot():
    assert preferred_instruments("USDRUB")[0] == {
        "ticker": "USD000SMALL",
        "classCode": "CETS_FX",
    }


def test_eurrub_prefers_verified_bcs_tom_instrument():
    assert preferred_instruments("EURRUB")[0] == {
        "ticker": "EUR_RUB__TOM",
        "classCode": "CETS",
    }


def test_perpetual_usdrub_futures_is_not_catalogued_as_base_spot():
    usdrub = preferred_instruments("USDRUB")
    assert all(item["ticker"] != "USDRUBF" for item in usdrub)
