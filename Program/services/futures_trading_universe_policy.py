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

    # Explicit Russian equity underlyings already represented by the project's
    # MOEX/BCS mapping. Foreign equities/ETFs and indices are intentionally absent.
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

    @classmethod
    def _root(cls, ticker):
        value = str(ticker or "").upper().strip().split("-", 1)[0]
        return re.sub(r"[FGHJKMNQUVXZ]\d$", "", value)

    @classmethod
    def _is_dated_contract(cls, ticker):
        value = str(ticker or "").upper().strip()
        # MOEX/BCS can expose the same dated contract as compact RFUD form
        # (SRU6) or broker display form (SBER-12.26 / Si-9.26).
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
        """Resolve an RFUD family to its economic underlying for hard filtering."""
        root = str(root or "").upper().strip()
        if root in cls.SPECIAL_ROOTS:
            return root
        from services.futures_oi_scanner_service import FuturesOIScannerService
        mapping = getattr(FuturesOIScannerService, "MOEX_SHORT_CODE_BY_UNDERLYING", {})
        for underlying, family in mapping.items():
            if str(family or "").upper() == root:
                return str(underlying).upper()
        return ""


def install_guard():
    """Install the locked universe at both futures admission boundaries."""
    from services.futures_oi_scanner_service import FuturesOIScannerService
    from services.open_interest_service import OpenInterestService

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

    original_working_marketdata_rows = OpenInterestService._working_marketdata_rows

    def guarded_working_marketdata_rows(self, rows, as_of=None):
        candidates = list(rows or [])
        allowed_rows = []
        reasons = {}
        for row in candidates:
            if not isinstance(row, dict):
                continue
            secid = str(row.get("secid") or row.get("ticker") or "").strip().upper()
            family = self._marketdata_family(secid)
            underlying = FuturesTradingUniversePolicy.marketdata_underlying(family)
            ok, reason = FuturesTradingUniversePolicy.classify(
                secid,
                family,
                underlying,
            )
            if ok:
                allowed_rows.append(row)
            else:
                reasons[reason] = reasons.get(reason, 0) + 1

        selected = original_working_marketdata_rows(self, allowed_rows, as_of=as_of)
        self._trading_universe_marketdata_diagnostics = {
            "trading_universe_marketdata_policy": FuturesTradingUniversePolicy.VERSION,
            "trading_universe_marketdata_candidates": len(candidates),
            "trading_universe_marketdata_allowed": len(allowed_rows),
            "trading_universe_marketdata_filtered": len(candidates) - len(allowed_rows),
            "trading_universe_marketdata_filter_reasons": reasons,
            "trading_universe_marketdata_scope": (
                "RUSSIAN_STOCKS_USDRUB_EURRUB_CNYRUB_BRENT_CL_NG_GOLD_ONLY"
            ),
        }
        return selected

    FuturesOIScannerService._active_contracts = guarded_active_contracts
    FuturesOIScannerService._trading_universe_guard_installed = True
    OpenInterestService._working_marketdata_rows = guarded_working_marketdata_rows
    OpenInterestService._trading_universe_marketdata_guard_installed = True
