from api.bcs_underlying_catalog import preferred_instruments


VERIFIED_TQBR = (
    "AFKS", "AFLT", "ALRS", "ASTR", "BANE", "BSPB", "CBOM", "MAGN",
    "MGNT", "MOEX", "MVID", "NLMK", "OZON", "PHOR", "POSI", "RAGR",
    "RASP", "RNFT", "ROSN", "RTKM", "WUSH", "X5", "YDEX",
)


def test_live_bcs_audit_verified_moex_stocks_have_exact_tqbr_preferences():
    for ticker in VERIFIED_TQBR:
        instruments = preferred_instruments(ticker)
        assert instruments == ({"ticker": ticker, "classCode": "TQBR"},)
