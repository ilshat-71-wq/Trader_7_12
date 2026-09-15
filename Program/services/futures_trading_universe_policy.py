"""Locked production futures trading universe.

Only dated MOEX futures from the project's declared trading scope are allowed:
- Russian single-stock futures;
- USD/RUB, EUR/RUB, CNY/RUB;
- Brent, Light Sweet Crude Oil, Natural Gas;
- Gold.

Perpetual/daily-auto-roll, crypto, foreign-stock/ETF, index, rate and other
products are excluded. Unknown/new products do not enter automatically.
"""

import re


class FuturesTradingUniversePolicy:
    VERSION = "1.0.2"

    SPECIAL_ROOTS = frozenset({"SI", "EU", "CR", "CNY", "BR", "CL", "NG", "GD", "GL"})
    FORBIDDEN_PERPETUAL_ROOTS = frozenset({"USDRUBF", "EURRUBF", "CNYRUBF", "GAZPF", "SBERF"})

    RUSSIAN_STOCK_UNDERLYINGS = frozenset({
        "AFLT", "ALRS", "AFKS", "CHMF", "FEES", "GAZP", "GMKN", "HYDR",
        "LKOH", "MGNT", "MOEX", "NLMK", "NOTK", "ROSN", "RTKM", "SBER",
        "SBERP", "SNGP", "SNGS", "TATN", "TATP", "TRNF", "VTBR", "MAGN",
        "PLZL", "YDEX", "SMLT", "POSI", "SPBE", "RUAL", "PHOR", "PIKK",
        "POLY", "RSTI", "SIBN", "TCSI", "VKCO", "WUSH", "MVID", "CBOM",
        "SGZH", "FLOT", "BSPB", "BANE", "KMAZ", "ASTR", "SOFL", "SVCB",
        "RASP", "FESH", "RNFT", "LEAS", "X5", "OZON", "DOMRF", "IVAT",
        "ENPG", "T", "FIXR", "RAGR",
    })

    # Authoritative RFUD family -> economic underlying aliases used at the
    # marketdata boundary. Keep this explicit: foreign/index/rate/crypto roots
    # must never become allowed merely because a broad catalog knows their name.
    MARKETDATA_ROOT_UNDERLYINGS = {
        "SBRF": "SBER", "SR": "SBER", "SP": "SBERP",
        "GAZR": "GAZP", "GZ": "GAZP", "LK": "LKOH",
        "AF": "AFLT", "AL": "ALRS", "AK": "AFKS", "CH": "CHMF",
        "FS": "FEES", "GK": "GMKN", "HY": "HYDR", "MN": "MGNT",
        "ME": "MOEX", "NM": "NLMK", "NK": "NOTK", "RN": "ROSN",
        "RT": "RTKM", "SG": "SNGP", "SN": "SNGS", "TT": "TATN",
        "TP": "TATP", "TN": "TRNF", "VB": "VTBR", "MG": "MAGN",
        "PZ": "PLZL", "YD": "YDEX", "SS": "SMLT", "PS": "POSI",
        "SE": "SPBE", "RL": "RUAL", "PH": "PHOR", "PI": "PIKK",
        "PO": "POLY", "RE": "RSTI", "SO": "SIBN", "TI": "TCSI",
        "VK": "VKCO", "WU": "WUSH", "MV": "MVID", "CM": "CBOM",
        "SZ": "SGZH", "FL": "FLOT", "BS": "BSPB", "BN": "BANE",
        "KM": "KMAZ", "AS": "ASTR", "S0": "SOFL", "SC": "SVCB",
        "RA": "RASP", "FE": "FESH", "RU": "RNFT", "LE": "LEAS",
        "X5": "X5", "ON": "OZON", "DR": "DOMRF", "IV": "IVAT",
        "EA": "ENPG", "TB": "T", "FI": "FIXR", "RZ": "RAGR",
    }

    @classmethod
    def _root(cls, ticker):
        value = str(ticker or "").upper().strip().split("-", 1)[0]
        return re.sub(r"[FGHJKMNQUVXZ]\d$", "", value)

    @classmethod
    def _is_dated_contract(cls, ticker):
        value = str(ticker or "").upper().strip()
        if re.match(r"^[A-Z0-9]+[FGHJKMNQUVXZ]\d$", value):
            return True
        if re.match(r"^[A-Z0-9]+-[0-9]{1,2}\.\d{2}$", value):
            return True
        return False

    @classmethod
    def classify(cls, ticker, oi_root="", underlying_ticker=""):
        ticker = str(ticker or "").upper().strip()
        root = str(oi_root or cls._root(ticker)).upper().strip()
        underlying = str(underlying_ticker or "").upper().strip()
        if not ticker:
            return False, "MISSING_TICKER"
        if root in cls.FORBIDDEN_PERPETUAL_ROOTS or ticker in cls.FORBIDDEN_PERPETUAL_ROOTS:
            return False, "PERPETUAL_OR_AUTO_ROLL"
        if not cls._is_dated_contract(ticker):
            return False, "NOT_DATED_MOEX_FUTURE"
        if root in cls.SPECIAL_ROOTS:
            return True, "APPROVED_CURRENCY_OR_COMMODITY"
        if underlying in cls.RUSSIAN_STOCK_UNDERLYINGS:
            return True, "APPROVED_RUSSIAN_STOCK"
        return False, "OUTSIDE_LOCKED_TRADING_UNIVERSE"

    @classmethod
    def is_allowed(cls, ticker, oi_root="", underlying_ticker=""):
        return cls.classify(ticker, oi_root, underlying_ticker)[0]

    @classmethod
    def reason(cls, ticker, oi_root="", underlying_ticker=""):
        return cls.classify(ticker, oi_root, underlying_ticker)[1]

    @classmethod
    def filter_contracts(cls, contracts):
        allowed = []
        reasons = {}
        for contract in contracts or []:
            ticker = contract.get("futures_ticker") or contract.get("ticker")
            root = contract.get("oi_root") or contract.get("futures_root")
            underlying = contract.get("underlying_ticker") or contract.get("underlying_asset_source")
            ok, reason = cls.classify(ticker, root, underlying)
            if ok:
                allowed.append(contract)
            else:
                reasons[reason] = reasons.get(reason, 0) + 1
        return allowed, reasons

    @classmethod
    def marketdata_underlying(cls, root):
        root = str(root or "").upper().strip()
        if root in cls.SPECIAL_ROOTS:
            return root
        return cls.MARKETDATA_ROOT_UNDERLYINGS.get(root, "")

    @classmethod
    def filter_marketdata(cls, rows):
        allowed = []
        reasons = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            secid = str(row.get("secid") or row.get("ticker") or "").strip().upper()
            family = cls._root(secid)
            underlying = cls.marketdata_underlying(family)
            ok, reason = cls.classify(secid, family, underlying)
            if ok:
                allowed.append(row)
            else:
                reasons[reason] = reasons.get(reason, 0) + 1
        return allowed, reasons


def install_guard():
    """Install the locked universe only at the BCS futures admission boundary.

    MOEX OpenInterestService remains independently testable and reusable. The
    production marketdata scanner is the authoritative consumer boundary.
    """
    from services.futures_oi_scanner_service import FuturesOIScannerService

    if getattr(FuturesOIScannerService, "_trading_universe_guard_installed", False):
        return

    original_active_contracts = FuturesOIScannerService._active_contracts

    def guarded_active_contracts(self):
        contracts = original_active_contracts(self)
        allowed, reasons = FuturesTradingUniversePolicy.filter_contracts(contracts)
        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics["trading_universe_policy"] = FuturesTradingUniversePolicy.VERSION
        diagnostics["trading_universe_candidates"] = len(contracts)
        diagnostics["trading_universe_allowed"] = len(allowed)
        diagnostics["trading_universe_filtered"] = len(contracts) - len(allowed)
        diagnostics["trading_universe_filter_reasons"] = reasons
        diagnostics["trading_universe_scope"] = (
            "RUSSIAN_STOCKS_USDRUB_EURRUB_CNYRUB_BRENT_CL_NG_GOLD_ONLY"
        )
        self._last_contract_diagnostics = diagnostics
        return allowed

    FuturesOIScannerService._active_contracts = guarded_active_contracts
    FuturesOIScannerService._trading_universe_guard_installed = True
