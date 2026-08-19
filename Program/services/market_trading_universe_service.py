"""Unified tradable SPOT universe for Trader_7_12 Pro.

Universe = current IMOEX equities + four independent macro markets:
OIL, GOLD, GAS and USDRUB.

The service does not invent instruments. It only classifies already-valid
Futures -> SPOT mappings and keeps the configured market groups.
"""


class MarketTradingUniverseService:
    VERSION = "1.0"

    IMOEX = "IMOEX"
    OIL = "OIL"
    GOLD = "GOLD"
    GAS = "GAS"
    USDRUB = "USDRUB"

    MACRO_GROUPS = (OIL, GOLD, GAS, USDRUB)
    TARGET_GROUPS = ("MOEX_STOCK", OIL, GOLD, GAS, USDRUB)

    # MOEX/BCS short futures codes. The suffix contains the expiry month/year.
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
    }

    @classmethod
    def futures_group(cls, futures_ticker):
        ticker = str(futures_ticker or "").strip().upper()
        if not ticker:
            return None
        # Longest prefixes first to avoid GLDRUBF being treated as GL.
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
