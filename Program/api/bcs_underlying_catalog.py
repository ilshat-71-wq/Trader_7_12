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
