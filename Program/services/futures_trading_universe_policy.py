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
    VERSION = "1.0.3"

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

    MARKETDATA_ROOT_UNDERLYINGS = {
        "SBRF": "SBER", "SR": "SBER", "SP": "SBERP", "GAZR": "GAZP", "GZ": "GAZP",
        "LK": "LKOH", "AF": "AFLT", "AL": "ALRS", "AK": "AFKS", "CH": "CHMF",
        "FS": "FEES", "GK": "GMKN", "HY": "HYDR", "MN": "MGNT", "ME": "MOEX",
        "NM": "NLMK", "NK": "NOTK", "RN": "ROSN", "RT": "RTKM", "SG": "SNGP",
        "SN": "SNGS", "TT": "TATN", "TP": "TATP", "TN": "TRNF", "VB": "VTBR",
        "MG": "MAGN", "PZ": "PLZL", "YD": "YDEX", "SS": "SMLT", "PS": "POSI",
        "SE": "SPBE", "RL": "RUAL", "PH": "PHOR", "PI": "PIKK", "PO": "POLY",
        "RE": "RSTI", "SO": "SIBN", "TI": "TCSI", "VK": "VKCO", "WU": "WUSH",
        "MV": "MVID", "CM": "CBOM", "SZ": "SGZH", "FL": "FLOT", "BS": "BSPB",
        "BN": "BANE", "KM": "KMAZ", "AS": "ASTR", "S0": "SOFL", "SC": "SVCB",
        "RA": "RASP", "FE": "FESH", "RU": "RNFT", "LE": "LEAS", "X5": "X5",
        "ON": "OZON", "DR": "DOMRF", "IV": "IVAT", "EA": "ENPG", "TB": "T",
        "FI": "FIXR", "RZ": "RAGR",
    }

    @classmethod
    def _root(cls, ticker):
        value = str(ticker or "").upper().strip().split("-", 1)[0]
        return re.sub(r"[FGHJKMNQUVXZ]\d$", "", value)

    @classmethod
    def _is_dated_contract(cls, ticker):
        value = str(ticker or "").upper().strip()
        return bool(
            re.match(r"^[A-Z0-9]+[FGHJKMNQUVXZ]\d$", value)
            or re.match(r"^[A-Z0-9]+-[0-9]{1,2}\.\d{2}$", value)
        )

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
    def filter_marketdata_map(cls, mapping):
        allowed = {}
        reasons = {}
        for family, row in (mapping or {}).items():
            family = str(family or "").upper().strip()
            row = dict(row or {})
            secid = str(row.get("_moex_working_contract") or row.get("secid") or row.get("ticker") or "").upper().strip()
            underlying = cls.marketdata_underlying(family)
            ok, reason = cls.classify(secid, family, underlying)
            if ok:
                allowed[family] = row
            else:
                reasons[reason] = reasons.get(reason, 0) + 1
        return allowed, reasons


def install_guard():
    """Install the locked universe at the actual production admission boundaries."""
    from services.futures_oi_scanner_service import FuturesOIScannerService
    from services.open_interest_service import OpenInterestService

    if not getattr(FuturesOIScannerService, "_trading_universe_guard_installed", False):
        original_active_contracts = FuturesOIScannerService._active_contracts

        def guarded_active_contracts(self):
            contracts = original_active_contracts(self)
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

    if not getattr(OpenInterestService, "_trading_universe_marketdata_guard_installed", False):
        original_front = getattr(OpenInterestService, "marketdata_front_contracts", None)
        original_curve = getattr(OpenInterestService, "marketdata_curve_contracts", None)

        if original_front:
            def guarded_front(self, *args, **kwargs):
                result = original_front(self, *args, **kwargs)
                allowed, reasons = FuturesTradingUniversePolicy.filter_marketdata_map(result)
                self._trading_universe_marketdata_diagnostics = {
                    "trading_universe_marketdata_policy": FuturesTradingUniversePolicy.VERSION,
                    "trading_universe_marketdata_candidates": len(result or {}),
                    "trading_universe_marketdata_allowed": len(allowed),
                    "trading_universe_marketdata_filtered": len(result or {}) - len(allowed),
                    "trading_universe_marketdata_filter_reasons": reasons,
                    "trading_universe_marketdata_scope": "RUSSIAN_STOCKS_USDRUB_EURRUB_CNYRUB_BRENT_CL_NG_GOLD_ONLY",
                }
                return allowed
            OpenInterestService.marketdata_front_contracts = guarded_front

        if original_curve:
            def guarded_curve(self, *args, **kwargs):
                result = original_curve(self, *args, **kwargs)
                allowed, _ = FuturesTradingUniversePolicy.filter_marketdata_map(result)
                return allowed
            OpenInterestService.marketdata_curve_contracts = guarded_curve

        OpenInterestService._trading_universe_marketdata_guard_installed = True
