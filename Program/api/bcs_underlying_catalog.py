"""Authoritative BCS economic-underlying instrument catalog.

The catalog contains the exact BCS ticker/classCode pairs used by Trader_7_12
when a futures contract must be enriched with its real economic underlying.

Important:
- futures/options are never valid underlying instruments;
- the catalog is a deterministic preference table, not a substitute for the
  live BCS instrument directory;
- live BCS metadata remains the final authority when the same economic asset
  is represented by more than one settlement instrument.

BCS documentation confirms that market-data requests identify instruments by
both ticker and classCode and that the instrument-directory endpoint exists
for ticker lookup.  Currency/metal settlement tickers below are based on the
BCS instrument lists used by the project.
"""

# canonical economic underlying -> preferred BCS instrument(s), in priority order
BCS_UNDERLYING_INSTRUMENTS = {
    "USDRUB": (
        {"ticker": "USDRUB_TOM", "classCode": "CETS"},
        {"ticker": "USDRUB_TOD", "classCode": "CETS"},
    ),
    "EURRUB": (
        {"ticker": "EURRUB_TOM", "classCode": "CETS"},
        {"ticker": "EURRUB_TOD", "classCode": "CETS"},
    ),
    "CNYRUB": (
        {"ticker": "CNYRUB_TOM", "classCode": "CETS"},
        {"ticker": "CNYRUB_TOD", "classCode": "CETS"},
    ),
    "GLDRUB_TOM": (
        {"ticker": "GLDRUB_TOM", "classCode": "CETS_MTL"},
    ),
    "IMOEX": (
        {"ticker": "IMOEX", "classCode": "INDX"},
    ),
    "RTS": (
        {"ticker": "RTS", "classCode": "INDX"},
    ),
    "RGBI": (
        {"ticker": "RGBI", "classCode": "INDX"},
    ),
    "SBER": (
        {"ticker": "SBER", "classCode": "TQBR"},
    ),
    # BCS metadata observed by the project exposes GAZP in the SMAL class.
    "GAZP": (
        {"ticker": "GAZP", "classCode": "SMAL"},
    ),
    "QQQ": (
        {"ticker": "QQQ", "classCode": "SPBXM"},
    ),
    "SPY": (
        {"ticker": "SPY", "classCode": "QMEBLCK"},
    ),

    # The following MOEX stock underlyings were verified against the live BCS
    # instrument catalog during the 2026-09-15 audit. Each exists in TQBR.
    "AFKS": ({"ticker": "AFKS", "classCode": "TQBR"},),
    "AFLT": ({"ticker": "AFLT", "classCode": "TQBR"},),
    "ALRS": ({"ticker": "ALRS", "classCode": "TQBR"},),
    "ASTR": ({"ticker": "ASTR", "classCode": "TQBR"},),
    "BANE": ({"ticker": "BANE", "classCode": "TQBR"},),
    "BSPB": ({"ticker": "BSPB", "classCode": "TQBR"},),
    "CBOM": ({"ticker": "CBOM", "classCode": "TQBR"},),
    "MAGN": ({"ticker": "MAGN", "classCode": "TQBR"},),
    "MGNT": ({"ticker": "MGNT", "classCode": "TQBR"},),
    "MOEX": ({"ticker": "MOEX", "classCode": "TQBR"},),
    "MVID": ({"ticker": "MVID", "classCode": "TQBR"},),
    "NLMK": ({"ticker": "NLMK", "classCode": "TQBR"},),
    "OZON": ({"ticker": "OZON", "classCode": "TQBR"},),
    "PHOR": ({"ticker": "PHOR", "classCode": "TQBR"},),
    "POSI": ({"ticker": "POSI", "classCode": "TQBR"},),
    "RAGR": ({"ticker": "RAGR", "classCode": "TQBR"},),
    "RASP": ({"ticker": "RASP", "classCode": "TQBR"},),
    "RNFT": ({"ticker": "RNFT", "classCode": "TQBR"},),
    "ROSN": ({"ticker": "ROSN", "classCode": "TQBR"},),
    "RTKM": ({"ticker": "RTKM", "classCode": "TQBR"},),
    "WUSH": ({"ticker": "WUSH", "classCode": "TQBR"},),
    "X5": ({"ticker": "X5", "classCode": "TQBR"},),
    "YDEX": ({"ticker": "YDEX", "classCode": "TQBR"},),
}


# Futures families -> canonical economic underlying.
CANONICAL_FUTURES_UNDERLYINGS = {
    "SI": "USDRUB",
    "USDRUBF": "USDRUB",
    "EU": "EURRUB",
    "CR": "CNYRUB",
    "CNY": "CNYRUB",
    "GD": "GLDRUB_TOM",
    "GL": "GLDRUB_TOM",
    "MX": "IMOEX",
    "MM": "IMOEX",
    "IMOEXF": "IMOEX",
    "RI": "RTS",
    "RM": "RTS",
    "SR": "SBER",
    "SBRF": "SBER",
    "GZ": "GAZP",
    "NA": "QQQ",
    "SF": "SPY",
    "RB": "RGBI",
}


def preferred_instruments(canonical_underlying: str):
    """Return preferred BCS ticker/classCode pairs for an underlying."""
    key = str(canonical_underlying or "").strip().upper()
    return BCS_UNDERLYING_INSTRUMENTS.get(key, ())
