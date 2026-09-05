"""Trader_7_12 Pro — current-session market-attention scanner."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, time

from services.spot_universe_service import SpotUniverseService
from services.history_candle_service import HistoryCandleService
from services.market_session_service import MarketSessionService
from services.relative_strength_service import RelativeStrengthService


class MarketAttentionScannerService:
    """Read-only scanner for real BASE/SPOT instruments only."""

    VERSION = "2.0"
    RECENT_MINUTES = 15
    MAX_WORKERS = 6
    SCAN_START = time(7, 0)
    SCAN_END = time(13, 0)
    BENCHMARKS = ("IMOEX2", "IRUS2")
    MACRO_ALIASES = {
        "GOLD": ("GLDRUB_TOM",),
        "USDRUB": ("USDRUB_TOM", "USDRUB_TOD", "USD000UTSTOM"),
        "OIL": ("BRENT", "BRENTOIL", "OIL"),
        "GAS": ("NATURALGAS", "NATURAL_GAS", "GAS"),
    }

    def __init__(self, api=None, history_service=None, session_service=None):
        from api.bcs_api import BCSAPI
        self.api = api or BCSAPI()
        self.history = history_service or HistoryCandleService()
        self.session = session_service or MarketSessionService()
        self.rs = RelativeStrengthService()
        self._last_scan_diagnostics = {}

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _metadata_by_alias(self, aliases):
        try:
            rows = self.api.get_instruments_by_tickers(list(aliases))
        except Exception:
            rows = []
        return rows if isinstance(rows, list) else []

    def build_universe(self):
        """Build only STOCK/TQBR plus real non-futures base instruments."""
        spots = SpotUniverseService(api=self.api).load()
        universe = []
        seen = set()
        seen_tickers = set()
        for row in spots:
            if row.get("spot_instrument_type") == "STOCK" and row.get("spot_class_code") == "TQBR":
                item = dict(row)
                item.update({"market_group": "STOCK", "market_label": "АКЦИИ", "spot_universe": "TQBR"})
                key = (item["spot_ticker"], item["spot_class_code"])
                if key not in seen:
                    seen.add(key)
                    seen_tickers.add(item["spot_ticker"])
                    universe.append(item)

        alias_pool = tuple(dict.fromkeys(x for group in self.MACRO_ALIASES.values() for x in group))
        for row in self._metadata_by_alias(alias_pool):
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or row.get("secCode") or row.get("securityCode") or "").strip().upper()
            code = str(row.get("classCode") or row.get("class_code") or "").strip()
            instrument_kind = str(row.get("type") or row.get("instrumentType") or row.get("securityType") or "").upper()
            if "FUT" in instrument_kind or "DERIV" in instrument_kind:
                continue
            if not ticker or not code or ticker in seen_tickers:
                continue
            for group, aliases in self.MACRO_ALIASES.items():
                if ticker in {x.upper() for x in aliases}:
                    seen.add((ticker, code))
                    seen_tickers.add(ticker)
                    universe.append({
                        "spot_ticker": ticker, "spot_class_code": code,
                        "spot_group": group, "market_group": group,
                        "market_label": group, "spot_universe": "BASE_ASSET_SPOT",
                        "spot_instrument_type": "BASE_SPOT",
                        "spot_name": str(row.get("name") or row.get("displayName") or ticker),
                    })
                    break
        return universe

    def _candles(self, ticker, class_code, start, end):
        try:
            rows = self.history.load(ticker, class_code, start_time=start, end_time=end, timeframe_minutes=5)
        except Exception:
            return []
        return rows if isinstance(rows, list) else []

    def _analyze_one(self, item, trading_date, session_start, now):
        ticker = item["spot_ticker"]
        class_code = item["spot_class_code"]
        start = datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE).astimezone(timezone.utc)
        candles = self._candles(ticker, class_code, start, now.astimezone(timezone.utc))
        if len(candles) < 2:
            return None
        candles.sort(key=lambda x: str(x.get("time") or ""))
        first = self._f(candles[0].get("close")); last = self._f(candles[-1].get("close"))
        if first <= 0 or last <= 0:
            return None
        total_money = sum(max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in candles)
        window_bars = max(1, self.RECENT_MINUTES // 5)
        recent = candles[-window_bars:]
        previous = candles[-2 * window_bars:-window_bars]
        recent_money = sum(max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in recent)
        previous_money = sum(max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in previous)
        elapsed = max(1, int((now - datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE)).total_seconds() / 60))
        pace = total_money / elapsed
        recent_elapsed = min(self.RECENT_MINUTES, elapsed)
        recent_pace = recent_money / max(1, recent_elapsed)
        previous_pace = previous_money / max(1, min(self.RECENT_MINUTES, elapsed))
        acceleration = (recent_pace / previous_pace - 1.0) if previous_pace > 0 else 0.0
        change = (last / first - 1.0) * 100.0
        direction = "LONG" if change > 0 else "SHORT" if change < 0 else "NEUTRAL"
        return {**item, "price": last, "change_percent": change, "direction": direction,
                "session_money": total_money, "money_per_minute": pace,
                "recent_money": recent_money, "recent_money_per_minute": recent_pace,
                "money_acceleration": acceleration * 100.0, "candle_count": len(candles),
                "data_status": "AVAILABLE"}

    def _benchmark(self, trading_date, now, session_start):
        for row in self._metadata_by_alias(self.BENCHMARKS):
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or row.get("secCode") or row.get("securityCode") or "").strip().upper()
            code = str(row.get("classCode") or row.get("class_code") or "").strip()
            if not ticker or not code:
                continue
            candles = self._candles(ticker, code,
                datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE).astimezone(timezone.utc),
                now.astimezone(timezone.utc))
            if len(candles) >= 2:
                first = self._f(candles[0].get("close")); last = self._f(candles[-1].get("close"))
                if first > 0 and last > 0:
                    return ticker, code, (last / first - 1.0) * 100.0
        return None, None, None

    @staticmethod
    def _percentile(value, values):
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return 100.0
        below = sum(1 for x in ordered if x < value)
        equal = sum(1 for x in ordered if x == value)
        return round((below + equal * 0.5) / len(ordered) * 100.0, 1)

    def scan(self, limit=3):
        if not self.api.access_token and not self.api.authorize():
            self._last_scan_diagnostics = {"status": "BCS_AUTH_FAILED"}
            return []
        info = self.session.get_session_info()
        session_name = str(info.get("session") or "MORNING").upper()
        trading_date = self.session.get_trading_day()
        now = self.session.now()
        if now.time() < self.SCAN_START or now.time() >= self.SCAN_END:
            self._last_scan_diagnostics = {"status": "OUTSIDE_SCAN_WINDOW", "scan_window": "07:00-13:00 MSK"}
            return []

        session_start = self.SCAN_START
        # Build metadata first. It is cheap and gives diagnostics even when
        # the market-data endpoint is temporarily unavailable.
        universe = self.build_universe()
        benchmark_ticker, benchmark_code, benchmark_change = self._benchmark(trading_date, now, session_start)

        # Never spend hundreds of HTTP candle requests when the benchmark is
        # unavailable: without it, the scanner is explicitly forbidden from
        # producing directional LONG/SHORT selections.
        if benchmark_change is None:
            self._last_scan_diagnostics = {
                "status": "BENCHMARK_UNAVAILABLE",
                "session": session_name,
                "trading_date": str(trading_date),
                "scan_window": "07:00-13:00 MSK",
                "universe_total": len(universe),
                "stocks_total": sum(1 for x in universe if x.get("market_group") == "STOCK"),
                "analyzed": 0,
                "benchmark": None,
                "benchmark_class_code": benchmark_code,
                "group_status": {group: ("AVAILABLE" if any(x.get("market_group") == group for x in universe) else "UNAVAILABLE") for group in ("STOCK", "GOLD", "OIL", "GAS", "USDRUB")},
                "data_policy": "SPOT_BASE_ONLY_NO_FUTURES",
            }
            return []

        results = []
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS, thread_name_prefix="attention") as pool:
            futures = [pool.submit(self._analyze_one, item, trading_date, session_start, now) for item in universe]
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception:
                    row = None
                if row:
                    results.append(row)

        recent_values = [self._f(x["recent_money_per_minute"]) for x in results]
        session_values = [self._f(x["session_money"]) for x in results]
        pace_values = [self._f(x["money_per_minute"]) for x in results]
        for row in results:
            row["benchmark"] = benchmark_ticker or ""
            row["benchmark_change_percent"] = benchmark_change
            row["relative_strength"] = round(row["change_percent"] - benchmark_change, 4)
            row["relative_strength_status"] = "AVAILABLE"
            activity = self._percentile(self._f(row["recent_money_per_minute"]), recent_values)
            session_score = self._percentile(self._f(row["session_money"]), session_values)
            pace_score = self._percentile(self._f(row["money_per_minute"]), pace_values)
            accel_score = max(0.0, min(100.0, 50.0 + self._f(row["money_acceleration"]) * 2.0))
            row["attention_score"] = round(0.45 * activity + 0.25 * session_score + 0.20 * pace_score + 0.10 * accel_score, 1)
            rs = row["relative_strength"]
            row["market_relation"] = "СИЛЬНЕЕ РЫНКА" if rs > 0 else "СЛАБЕЕ РЫНКА" if rs < 0 else "НЕЙТРАЛЬНО"
            row["direction"] = "LONG" if rs > 0 else "SHORT" if rs < 0 else "NEUTRAL"

        valid = [x for x in results if x["relative_strength"] is not None and x["direction"] in {"LONG", "SHORT"}]
        strong = sorted((x for x in valid if x["relative_strength"] > 0), key=lambda x: (x["attention_score"], x["relative_strength"], x["recent_money_per_minute"]), reverse=True)
        weak = sorted((x for x in valid if x["relative_strength"] < 0), key=lambda x: (x["attention_score"], -x["relative_strength"], x["recent_money_per_minute"]), reverse=True)
        selected = []
        if strong:
            selected.append(dict(strong[0], selection_role="LONG_CANDIDATE", rank=1))
        if weak and (not selected or weak[0]["spot_ticker"] != selected[0]["spot_ticker"]):
            selected.append(dict(weak[0], selection_role="SHORT_CANDIDATE", rank=len(selected) + 1))
        selected_tickers = {x["spot_ticker"] for x in selected}
        remaining = sorted((x for x in valid if x["spot_ticker"] not in selected_tickers), key=lambda x: x["attention_score"], reverse=True)
        for row in remaining[:max(0, int(limit or 0) - len(selected))]:
            selected.append(dict(row, selection_role="ATTENTION_WATCH", rank=len(selected) + 1))
        for i, row in enumerate(selected, 1):
            row["rank"] = i
            row["pipeline_version"] = self.VERSION
        self._last_scan_diagnostics = {
            "status": "OK", "session": session_name, "trading_date": str(trading_date),
            "scan_window": "07:00-13:00 MSK", "universe_total": len(universe),
            "stocks_total": sum(1 for x in universe if x.get("market_group") == "STOCK"),
            "analyzed": len(results), "benchmark": benchmark_ticker,
            "benchmark_change_percent": benchmark_change, "selected": len(selected),
            "long_candidate": next((x["spot_ticker"] for x in selected if x["selection_role"] == "LONG_CANDIDATE"), None),
            "short_candidate": next((x["spot_ticker"] for x in selected if x["selection_role"] == "SHORT_CANDIDATE"), None),
            "group_status": {group: ("AVAILABLE" if any(x.get("market_group") == group for x in universe) else "UNAVAILABLE") for group in ("STOCK", "GOLD", "OIL", "GAS", "USDRUB")},
            "data_policy": "SPOT_BASE_ONLY_NO_FUTURES",
        }
        return selected
