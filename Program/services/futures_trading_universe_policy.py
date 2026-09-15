"""Locked production futures trading universe."""

import re


class FuturesTradingUniversePolicy:
    VERSION = "1.0.4"
    SPECIAL_ROOTS = frozenset({"SI", "EU", "CR", "CNY", "BR", "CL", "NG", "GD", "GL"})
    FORBIDDEN_PERPETUAL_ROOTS = frozenset({"USDRUBF", "EURRUBF", "CNYRUBF", "GAZPF", "SBERF"})
    RUSSIAN_STOCK_UNDERLYINGS = frozenset({
        "AFLT", "ALRS", "AFKS", "CHMF", "FEES", "GAZP", "GMKN", "HYDR", "LKOH", "MGNT",
        "MOEX", "NLMK", "NOTK", "ROSN", "RTKM", "SBER", "SBERP", "SNGP", "SNGS", "TATN",
        "TATP", "TRNF", "VTBR", "MAGN", "PLZL", "YDEX", "SMLT", "POSI", "SPBE", "RUAL",
        "PHOR", "PIKK", "POLY", "RSTI", "SIBN", "TCSI", "VKCO", "WUSH", "MVID", "CBOM",
        "SGZH", "FLOT", "BSPB", "BANE", "KMAZ", "ASTR", "SOFL", "SVCB", "RASP", "FESH",
        "RNFT", "LEAS", "X5", "OZON", "DOMRF", "IVAT", "ENPG", "T", "FIXR", "RAGR",
    })

    @classmethod
    def _root(cls, ticker):
        value = str(ticker or "").upper().strip().split("-", 1)[0]
        return re.sub(r"[FGHJKMNQUVXZ]\d$", "", value)

    @classmethod
    def _is_dated_contract(cls, ticker):
        value = str(ticker or "").upper().strip()
        return bool(re.match(r"^[A-Z0-9]+[FGHJKMNQUVXZ]\d$", value) or re.match(r"^[A-Z0-9]+-[0-9]{1,2}\.\d{2}$", value))

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
    def filter_contracts(cls, contracts):
        allowed, reasons = [], {}
        for contract in contracts or []:
            ok, reason = cls.classify(contract.get("futures_ticker") or contract.get("ticker"), contract.get("oi_root") or contract.get("futures_root"), contract.get("underlying_ticker") or contract.get("underlying_asset_source"))
            if ok:
                allowed.append(contract)
            else:
                reasons[reason] = reasons.get(reason, 0) + 1
        return allowed, reasons


def install_guard():
    """Hard-filter only at the production scanner admission boundary."""
    from services.futures_oi_scanner_service import FuturesOIScannerService
    if getattr(FuturesOIScannerService, "_trading_universe_guard_installed", False):
        return
    original = FuturesOIScannerService._active_contracts
    def guarded_active_contracts(self):
        contracts = original(self)
        allowed, reasons = FuturesTradingUniversePolicy.filter_contracts(contracts)
        diagnostics = dict(getattr(self, "_last_contract_diagnostics", {}))
        diagnostics.update({
            "trading_universe_policy": FuturesTradingUniversePolicy.VERSION,
            "trading_universe_candidates": len(contracts),
            "trading_universe_allowed": len(allowed),
            "trading_universe_filtered": len(contracts) - len(allowed),
            "trading_universe_filter_reasons": reasons,
            "trading_universe_scope": "RUSSIAN_STOCKS_USDRUB_EURRUB_CNYRUB_BRENT_CL_NG_GOLD_ONLY",
        })
        self._last_contract_diagnostics = diagnostics
        return allowed
    FuturesOIScannerService._active_contracts = guarded_active_contracts
    FuturesOIScannerService._trading_universe_guard_installed = True
