"""Unified tradable market universe for Trader_7_12 Pro.

Equities are discovered from the complete canonical MOEX TQBR universe.
Macro groups are classified from current BCS futures metadata so the scanner
can cover oil, gold, gas and multiple RUB currency futures without a fixed
instrument list.
"""


class MarketTradingUniverseService:
    VERSION = "1.1"

    IMOEX = "IMOEX"
    OIL = "OIL"
    GOLD = "GOLD"
    GAS = "GAS"
    USDRUB = "USDRUB"
    FX = "FX"

    MACRO_GROUPS = (OIL, GOLD, GAS, USDRUB, FX)
    TARGET_GROUPS = ("MOEX_STOCK", OIL, GOLD, GAS, USDRUB, FX)

    # BCS/MOEX futures prefixes.  The suffix normally contains the
    # conventional month/year expiry code.  Classification is deliberately
    # broad because BCS metadata can expose several contract families.
    FUTURES_PREFIX_GROUPS = {
        "BR": OIL,
        "BRM": OIL,
        "CL": OIL,
        "WT": OIL,
        "WTI": OIL,
        "GD": GOLD,
        "GOLD": GOLD,
        "GL": GOLD,
        "GOLDM": GOLD,
        "GLDRUBF": GOLD,
        "NG": GAS,
        "NGM": GAS,
        "FF": GAS,
        "TTF": GAS,
        "SI": USDRUB,
        "USDRUBF": USDRUB,
        "EU": FX,
        "ER": FX,
        "EUR": FX,
        "EURRUBF": FX,
        "CNY": FX,
        "CNYRUBF": FX,
        "CR": FX,
        "KZT": FX,
        "KZTRUBF": FX,
    }

    @classmethod
    def futures_group(cls, futures_ticker):
        ticker = str(futures_ticker or "").strip().upper()
        if not ticker:
            return None
        for prefix in sorted(cls.FUTURES_PREFIX_GROUPS, key=len, reverse=True):
            if ticker.startswith(prefix):
                return cls.FUTURES_PREFIX_GROUPS[prefix]
        return None

    @classmethod
    def spot_group(cls, mapping):
        if not isinstance(mapping, dict):
            return None
        explicit = str(mapping.get("spot_group") or "").strip().upper()
        if explicit in cls.TARGET_GROUPS:
            return explicit

        class_code = str(mapping.get("spot_class_code") or "").strip().upper()
        if class_code == "TQBR":
            return "MOEX_STOCK"

        return cls.futures_group(mapping.get("futures_ticker"))

    @classmethod
    def filter_mappings(cls, mappings):
        if not isinstance(mappings, list):
            return []

        result = []
        seen = set()
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            group = cls.spot_group(mapping)
            if group not in cls.TARGET_GROUPS:
                continue

            item = dict(mapping)
            item["spot_group"] = group
            item["market_universe"] = cls.IMOEX if group == "MOEX_STOCK" else group

            key = (
                group,
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("futures_ticker") or "").strip().upper(),
                str(item.get("futures_class_code") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @classmethod
    def counts(cls, mappings):
        counts = {group: 0 for group in cls.TARGET_GROUPS}
        for mapping in mappings or []:
            group = cls.spot_group(mapping)
            if group in counts:
                counts[group] += 1
        return counts
