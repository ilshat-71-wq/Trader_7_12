"""Broad market money-first discovery for Trader_7_12 Pro.

The production scanner must not restrict equity discovery to IMOEX.  This
service loads the complete canonical MOEX TQBR stock universe and ranks every
instrument by money traded in the active session before expensive trend/setup
analysis is performed.

The service is discovery-only.  It never places orders and never treats the
money ranking as a trading signal by itself.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time


class BroadMarketMoneyScannerService:
    VERSION = "1.0"
    MONEY_WORKERS = 4
    CACHE_SECONDS = 90
    MAX_STOCKS_FOR_DEEP_ANALYSIS = 25

    def __init__(self, spot_universe_service, session_money_service, session_service):
        self.spot_universe_service = spot_universe_service
        self.session_money_service = session_money_service
        self.session_service = session_service
        self._cache = None
        self._cache_at = 0.0

    def load_all_tqbr_stocks(self):
        """Return every current BCS STOCK instrument on canonical MOEX TQBR."""
        spots = self.spot_universe_service.load()
        result = []
        seen = set()
        for item in spots or []:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("spot_ticker") or "").strip().upper()
            class_code = str(item.get("spot_class_code") or "").strip().upper()
            instrument_type = str(item.get("spot_instrument_type") or "").strip().upper()
            if not ticker or class_code != "TQBR" or instrument_type != "STOCK":
                continue
            if ticker in seen:
                continue
            seen.add(ticker)
            result.append({
                "spot_ticker": ticker,
                "spot_class_code": "TQBR",
                "spot_group": "MOEX_STOCK",
                "spot_universe": "ALL_TQBR_STOCKS",
                "market_universe": "ALL_TQBR_STOCKS",
                "spot_type": "SPOT",
                "spot_name": ticker,
                "mapping_method": "DIRECT_SPOT_UNIVERSE",
                "futures_ticker": "",
                "futures_class_code": "",
                "futures_expiry": None,
            })
        result.sort(key=lambda x: x["spot_ticker"])
        return result

    def _money_one(self, item, trading_date, session):
        ticker = item["spot_ticker"]
        class_code = item["spot_class_code"]
        try:
            data = self.session_money_service.calculate(
                ticker,
                class_code,
                trading_date=trading_date,
                timeframe_minutes=5,
                session=session,
            ) or {}
        except Exception as exc:
            return item, {
                "status": "ERROR",
                "error": type(exc).__name__,
                "money_volume": 0.0,
                "money_per_minute": 0.0,
                "elapsed_minutes": 0,
                "expected_minutes": 0,
            }

        def number(value):
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        return item, {
            "status": "OK",
            "money_volume": number(data.get("money_volume")),
            "money_per_minute": number(data.get("money_per_minute")),
            "elapsed_minutes": int(number(data.get("elapsed_minutes"))),
            "expected_minutes": int(number(data.get("expected_minutes"))),
        }

    def rank_current_money(self, force=False):
        """Rank the complete stock universe by current-session money/pace."""
        now = time.monotonic()
        if not force and self._cache is not None and now - self._cache_at < self.CACHE_SECONDS:
            return [dict(x) for x in self._cache]

        stocks = self.load_all_tqbr_stocks()
        if not stocks:
            self._cache = []
            self._cache_at = now
            return []

        session = self.session_service.get_session()
        trading_date = self.session_service.get_trading_day()
        ranked = []
        with ThreadPoolExecutor(
            max_workers=min(self.MONEY_WORKERS, len(stocks)),
            thread_name_prefix="money-discovery",
        ) as executor:
            futures = [
                executor.submit(self._money_one, item, trading_date, session)
                for item in stocks
            ]
            for future in as_completed(futures):
                item, money = future.result()
                row = dict(item)
                row.update({
                    "money_scan_status": money.get("status", "ERROR"),
                    "spot_session_money": round(float(money.get("money_volume", 0) or 0), 2),
                    "spot_money_per_minute": round(float(money.get("money_per_minute", 0) or 0), 2),
                    "session_elapsed_minutes": int(money.get("elapsed_minutes", 0) or 0),
                    "session_expected_minutes": int(money.get("expected_minutes", 0) or 0),
                })
                ranked.append(row)

        ranked.sort(
            key=lambda x: (
                float(x.get("spot_session_money", 0) or 0),
                float(x.get("spot_money_per_minute", 0) or 0),
                str(x.get("spot_ticker") or ""),
            ),
            reverse=True,
        )
        for rank, row in enumerate(ranked, 1):
            row["money_rank"] = rank

        self._cache = [dict(x) for x in ranked]
        self._cache_at = now
        return ranked

    def top_for_deep_analysis(self, limit=None, force=False):
        ranked = self.rank_current_money(force=force)
        if limit is None:
            limit = self.MAX_STOCKS_FOR_DEEP_ANALYSIS
        limit = max(0, int(limit))
        return ranked[:limit]
