"""Trader_7_12 Pro — current-session market-attention scanner."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, time

from services.spot_universe_service import SpotUniverseService
from services.history_candle_service import HistoryCandleService
from services.market_session_service import MarketSessionService
from services.daily_trend_profile_service import DailyTrendProfileService


class MarketAttentionScannerService:
    """Read-only scanner for real BASE/SPOT instruments only."""

    VERSION = "2.3.1"
    RECENT_MINUTES = 15
    MAX_WORKERS = 6
    MIN_DIRECTIONAL_COVERAGE = 0.80
    MIN_MEANINGFUL_RS_PP = 0.10
    # Absolute activity gates. They are scanner-operational thresholds, not MOEX
    # liquidity classifications. They prevent percentile ranking from promoting
    # economically insignificant instruments merely because the rest of the
    # scanned universe is even quieter.
    MIN_MONEY_PER_MINUTE = 8_000.0
    MIN_RECENT_MONEY_PER_MINUTE = 5_000.0
    RS_SCORE_WEIGHT = 0.60
    ATTENTION_SCORE_WEIGHT = 0.40
    SCAN_START = time(7, 0)
    PREFERRED_START = time(9, 50)
    PREFERRED_END = time(13, 0)
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
        self._last_scan_diagnostics = {}

    @staticmethod
    def _f(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metadata_ticker(row):
        if not isinstance(row, dict):
            return ""
        return str(row.get("ticker") or row.get("secCode") or row.get("securityCode") or "").strip().upper()

    @staticmethod
    def _metadata_class_code(row):
        if not isinstance(row, dict):
            return ""
        code = str(row.get("classCode") or row.get("class_code") or "").strip()
        if code:
            return code
        boards = row.get("boards")
        if not isinstance(boards, list):
            return ""
        candidates = []
        for board in boards:
            if not isinstance(board, dict):
                continue
            board_code = str(board.get("classCode") or board.get("class_code") or "").strip()
            if not board_code:
                continue
            exchange = str(board.get("exchange") or "").strip().upper()
            candidates.append((exchange == "MOEX", board_code))
        for is_moex, board_code in candidates:
            if is_moex:
                return board_code
        return candidates[0][1] if candidates else ""

    def _metadata_by_alias(self, aliases):
        try:
            rows = self.api.get_instruments_by_tickers(list(aliases))
        except Exception:
            rows = []
        return rows if isinstance(rows, list) else []

    def build_universe(self):
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
            ticker = self._metadata_ticker(row)
            code = self._metadata_class_code(row)
            kind = str(row.get("type") or row.get("instrumentType") or row.get("securityType") or "").upper()
            if "FUT" in kind or "DERIV" in kind or not ticker or not code or ticker in seen_tickers:
                continue
            for group, aliases in self.MACRO_ALIASES.items():
                if ticker in {x.upper() for x in aliases}:
                    seen.add((ticker, code)); seen_tickers.add(ticker)
                    universe.append({"spot_ticker": ticker, "spot_class_code": code,
                                     "spot_group": group, "market_group": group, "market_label": group,
                                     "spot_universe": "BASE_ASSET_SPOT", "spot_instrument_type": "BASE_SPOT",
                                     "spot_name": str(row.get("name") or row.get("displayName") or ticker)})
                    break
        return universe

    def _candles(self, ticker, class_code, start, end):
        try:
            rows = self.history.load(ticker, class_code, start_time=start, end_time=end, timeframe_minutes=5)
        except Exception:
            return []
        return rows if isinstance(rows, list) else []

    def _daily_candles(self, ticker, class_code, trading_date):
        try:
            rows = self.history.load_daily(ticker, class_code)
        except Exception:
            return []
        if not isinstance(rows, list):
            return []
        completed, seen_dates = [], set()
        for candle in rows:
            if not isinstance(candle, dict):
                continue
            value = candle.get("time") or candle.get("date") or candle.get("trading_date")
            try:
                dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                day = dt.astimezone(self.session.TIMEZONE).date()
            except (TypeError, ValueError):
                continue
            if day >= trading_date or day in seen_dates:
                continue
            seen_dates.add(day); completed.append(candle)
        completed.sort(key=lambda x: str(x.get("time") or x.get("date") or ""))
        return completed[-DailyTrendProfileService.MAX_DAYS:]

    def _daily_profile(self, item, trading_date, benchmark_daily):
        candles = self._daily_candles(item["spot_ticker"], item["spot_class_code"], trading_date)
        return DailyTrendProfileService.analyze(candles, benchmark_daily, before_date=trading_date)

    def _analyze_one(self, item, trading_date, session_start, now):
        ticker, class_code = item["spot_ticker"], item["spot_class_code"]
        start = datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE).astimezone(timezone.utc)
        candles = self._candles(ticker, class_code, start, now.astimezone(timezone.utc))
        if len(candles) < 2:
            return None
        candles.sort(key=lambda x: str(x.get("time") or ""))
        first, last = self._f(candles[0].get("close")), self._f(candles[-1].get("close"))
        if first <= 0 or last <= 0:
            return None
        money = [max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in candles]
        total_money = sum(money); window_bars = max(1, self.RECENT_MINUTES // 5)
        recent, previous = candles[-window_bars:], candles[-2 * window_bars:-window_bars]
        recent_money = sum(max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in recent)
        previous_money = sum(max(0.0, self._f(x.get("money_volume", x.get("volume")))) for x in previous)
        elapsed = max(1, int((now - datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE)).total_seconds() / 60))
        pace = total_money / elapsed
        recent_minutes = len(recent) * 5; previous_minutes = len(previous) * 5
        if len(recent) == window_bars and len(previous) == window_bars and previous_money > 0:
            recent_pace = recent_money / recent_minutes
            previous_pace = previous_money / previous_minutes
            acceleration = recent_pace / previous_pace - 1.0
        else:
            recent_pace = recent_money / max(1, recent_minutes); acceleration = 0.0
        change = (last / first - 1.0) * 100.0
        return {**item, "price": last, "change_percent": change,
                "direction": "LONG" if change > 0 else "SHORT" if change < 0 else "NEUTRAL",
                "session_money": total_money, "money_per_minute": pace,
                "recent_money": recent_money, "recent_money_per_minute": recent_pace,
                "money_acceleration": acceleration * 100.0, "candle_count": len(candles), "data_status": "AVAILABLE"}

    def _quote_session_return(self, ticker, class_code, now):
        try:
            data = self.api.get_quotes([{"ticker": ticker, "classCode": class_code}])
        except Exception:
            return None
        records = data.get("records", []) if isinstance(data, dict) else []
        record = next((x for x in records if isinstance(x, dict)), None) if isinstance(records, list) else None
        if not record:
            return None
        def first_positive(keys):
            for key in keys:
                value = self._f(record.get(key))
                if value > 0: return value
            return None
        last = first_positive(("lastPrice", "last", "price", "currentPrice", "close")); opening = first_positive(("openPrice", "open", "dayOpen", "openingPrice"))
        if last is None or opening is None: return None
        for key in ("dateTime", "datetime", "time", "timestamp"):
            value = record.get(key)
            if not value: continue
            try:
                timestamp = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
                if timestamp.tzinfo is None: timestamp = timestamp.replace(tzinfo=timezone.utc)
                if abs((now.astimezone(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds()) > 15 * 60: return None
                break
            except (TypeError, ValueError):
                continue
        return (last / opening - 1.0) * 100.0

    def _benchmark(self, trading_date, now, session_start):
        rows = self._metadata_by_alias(self.BENCHMARKS); by_ticker = {}
        for row in rows:
            ticker, code = self._metadata_ticker(row), self._metadata_class_code(row)
            if ticker and code: by_ticker[ticker] = (ticker, code)
        if any(t not in by_ticker for t in self.BENCHMARKS):
            try: index_rows = self.api.get_instruments("INDICES")
            except Exception: index_rows = []
            for row in index_rows if isinstance(index_rows, list) else []:
                ticker, code = self._metadata_ticker(row), self._metadata_class_code(row)
                if ticker in self.BENCHMARKS and code: by_ticker[ticker] = (ticker, code)
        start = datetime.combine(trading_date, session_start, tzinfo=self.session.TIMEZONE).astimezone(timezone.utc); end = now.astimezone(timezone.utc)
        for requested in self.BENCHMARKS:
            instrument = by_ticker.get(requested)
            if not instrument: continue
            ticker, code = instrument; candles = self._candles(ticker, code, start, end)
            if len(candles) >= 2:
                candles.sort(key=lambda x: str(x.get("time") or "")); first = self._f(candles[0].get("close")); last = self._f(candles[-1].get("close"))
                if first > 0 and last > 0: return ticker, code, (last / first - 1.0) * 100.0
            quote_return = self._quote_session_return(ticker, code, now)
            if quote_return is not None: return ticker, code, quote_return
        return None, None, None

    def _benchmark_daily(self, ticker, class_code, trading_date):
        return self._daily_candles(ticker, class_code, trading_date)

    @staticmethod
    def _percentile(value, values):
        if not values: return 0.0
        ordered = sorted(values)
        if len(ordered) == 1: return 100.0
        below = sum(1 for x in ordered if x < value); equal = sum(1 for x in ordered if x == value)
        return round((below + equal * 0.5) / len(ordered) * 100.0, 1)

    def _liquidity_ok(self, row):
        session_pace = self._f(row.get("money_per_minute")); recent_pace = self._f(row.get("recent_money_per_minute"))
        return session_pace >= self.MIN_MONEY_PER_MINUTE and recent_pace >= self.MIN_RECENT_MONEY_PER_MINUTE

    def scan(self, limit=3):
        if not self.api.access_token and not self.api.authorize():
            self._last_scan_diagnostics = {"status": "BCS_AUTH_FAILED"}; return []
        info = self.session.get_session_info(); session_name = str(info.get("session") or "MORNING").upper(); trading_date = self.session.get_trading_day(); now = self.session.now()
        if not self.session.is_market_open(now):
            self._last_scan_diagnostics = {"status": "MARKET_CLOSED", "session": "CLOSED", "trading_date": str(trading_date), "scan_window": "ВСЯ ТЕКУЩАЯ ТОРГОВАЯ СЕССИЯ", "preferred_window": "09:50-13:00 MSK", "universe_total": 0, "stocks_total": 0, "analyzed": 0, "benchmark": None, "data_policy": "SPOT_BASE_ONLY_NO_FUTURES"}; return []
        session_start = self.session.get_session_start(now)
        if session_start is None:
            self._last_scan_diagnostics = {"status": "MARKET_CLOSED", "session": session_name}; return []
        preferred = self.PREFERRED_START <= now.time() < self.PREFERRED_END; scan_window = f"{session_start.strftime('%H:%M')}-до закрытия MSK"; universe = self.build_universe()
        benchmark_ticker, benchmark_code, benchmark_change = self._benchmark(trading_date, now, session_start)
        if benchmark_change is None:
            self._last_scan_diagnostics = {"status": "BENCHMARK_UNAVAILABLE", "session": session_name, "trading_date": str(trading_date), "scan_window": scan_window, "preferred_window": "09:50-13:00 MSK", "preferred_window_active": preferred, "universe_total": len(universe), "stocks_total": sum(1 for x in universe if x.get("market_group") == "STOCK"), "analyzed": 0, "benchmark": None, "benchmark_class_code": benchmark_code, "group_status": {g: ("AVAILABLE" if any(x.get("market_group") == g for x in universe) else "UNAVAILABLE") for g in ("STOCK", "GOLD", "OIL", "GAS", "USDRUB")}, "data_policy": "SPOT_BASE_ONLY_NO_FUTURES"}; return []
        benchmark_daily = self._benchmark_daily(benchmark_ticker, benchmark_code, trading_date); daily_benchmark_available = len(benchmark_daily) >= DailyTrendProfileService.MIN_DAYS
        results = []; skipped = {"INSUFFICIENT_M5": [], "INVALID_RESULT": [], "WORKER_ERROR": [], "D1_UNAVAILABLE": [], "LOW_LIQUIDITY": []}
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS, thread_name_prefix="attention") as pool:
            future_items = {pool.submit(self._analyze_one, item, trading_date, session_start, now): item for item in universe}
            for future in as_completed(future_items):
                item = future_items[future]; ticker = str(item.get("spot_ticker") or "")
                try: row = future.result()
                except Exception: skipped["WORKER_ERROR"].append(ticker); continue
                if row: results.append(row)
                else: skipped["INSUFFICIENT_M5"].append(ticker)
        recent_values = [self._f(x["recent_money_per_minute"]) for x in results]; session_values = [self._f(x["session_money"]) for x in results]; pace_values = [self._f(x["money_per_minute"]) for x in results]; acceleration_values = [self._f(x["money_acceleration"]) for x in results]
        for row in results:
            row["benchmark"] = benchmark_ticker or ""; row["benchmark_change_percent"] = benchmark_change; row["relative_strength"] = round(row["change_percent"] - benchmark_change, 4); row["relative_strength_status"] = "AVAILABLE"
            row["liquidity_status"] = "PASS" if self._liquidity_ok(row) else "LOW_LIQUIDITY"
            row["liquidity_gate"] = row["liquidity_status"] == "PASS"
            activity = self._percentile(self._f(row["recent_money_per_minute"]), recent_values); session_score = self._percentile(self._f(row["session_money"]), session_values); pace_score = self._percentile(self._f(row["money_per_minute"]), pace_values); accel_score = self._percentile(self._f(row["money_acceleration"]), acceleration_values)
            row["attention_score"] = round(0.45 * activity + 0.25 * session_score + 0.20 * pace_score + 0.10 * accel_score, 1)
            if not row["liquidity_gate"]: skipped["LOW_LIQUIDITY"].append(row["spot_ticker"])
        for row in results:
            if daily_benchmark_available:
                try: profile = self._daily_profile(row, trading_date, benchmark_daily)
                except Exception: profile = {"direction": "NEUTRAL", "qualified": False, "structure_direction": "NEUTRAL", "structure_state": "ERROR", "relative_direction": "UNAVAILABLE", "days": 0}
                row["daily_profile"] = profile; row["daily_structure"] = profile.get("structure_direction", "NEUTRAL"); row["daily_structure_state"] = profile.get("structure_state", "UNKNOWN"); row["daily_relative_direction"] = profile.get("relative_direction", "UNAVAILABLE"); row["daily_relative_mean_pp"] = profile.get("relative_mean_pp", 0.0); row["daily_qualified"] = bool(profile.get("qualified"))
            else:
                row["daily_profile"] = {"direction": "NEUTRAL", "qualified": False, "structure_direction": "NEUTRAL", "structure_state": "D1_BENCHMARK_UNAVAILABLE", "relative_direction": "UNAVAILABLE", "days": 0}; row["daily_structure"] = "NEUTRAL"; row["daily_structure_state"] = "D1_BENCHMARK_UNAVAILABLE"; row["daily_relative_direction"] = "UNAVAILABLE"; row["daily_relative_mean_pp"] = 0.0; row["daily_qualified"] = False; skipped["D1_UNAVAILABLE"].append(row["spot_ticker"])
        rs_magnitudes = [abs(self._f(x.get("relative_strength"))) for x in results]
        for row in results:
            rs = self._f(row["relative_strength"]); rs_magnitude_score = self._percentile(abs(rs), rs_magnitudes); row["relative_strength_score"] = round(rs_magnitude_score, 1); row["directional_score"] = round(self.RS_SCORE_WEIGHT * rs_magnitude_score + self.ATTENTION_SCORE_WEIGHT * row["attention_score"], 1); row["relative_strength_quality"] = "MEANINGFUL" if abs(rs) >= self.MIN_MEANINGFUL_RS_PP else "WEAK"; row["market_relation"] = "СИЛЬНЕЕ РЫНКА" if rs > 0 else "СЛАБЕЕ РЫНКА" if rs < 0 else "НЕЙТРАЛЬНО"; intraday_direction = "LONG" if rs >= self.MIN_MEANINGFUL_RS_PP else "SHORT" if rs <= -self.MIN_MEANINGFUL_RS_PP else "NEUTRAL"; d1_direction = row.get("daily_profile", {}).get("direction", "NEUTRAL"); row["direction"] = intraday_direction if intraday_direction == d1_direction else "NEUTRAL"; row["directional_qualified"] = row["direction"] in {"LONG", "SHORT"} and row.get("daily_qualified", False) and row.get("liquidity_gate", False)
        valid = [x for x in results if x.get("directional_qualified")]; strong = sorted((x for x in valid if x["direction"] == "LONG"), key=lambda x: (x["directional_score"], x["relative_strength"], x["attention_score"], x["recent_money_per_minute"]), reverse=True); weak = sorted((x for x in valid if x["direction"] == "SHORT"), key=lambda x: (x["directional_score"], abs(x["relative_strength"]), x["attention_score"], x["recent_money_per_minute"]), reverse=True)
        selected = []
        if strong: selected.append(dict(strong[0], selection_role="LONG_CANDIDATE", rank=1))
        if weak and (not selected or weak[0]["spot_ticker"] != selected[0]["spot_ticker"]): selected.append(dict(weak[0], selection_role="SHORT_CANDIDATE", rank=len(selected) + 1))
        selected_tickers = {x["spot_ticker"] for x in selected}; remaining = sorted((x for x in valid if x["spot_ticker"] not in selected_tickers), key=lambda x: (x["directional_score"], x["attention_score"]), reverse=True)
        for row in remaining[:max(0, int(limit or 0) - len(selected))]: selected.append(dict(row, selection_role="ATTENTION_WATCH", rank=len(selected) + 1))
        for i, row in enumerate(selected, 1): row["rank"] = i; row["pipeline_version"] = self.VERSION; row["preferred_window_active"] = preferred
        coverage_ratio = (len(results) / len(universe)) if universe else 0.0; coverage_percent = round(coverage_ratio * 100.0, 1); coverage_ok = coverage_ratio >= self.MIN_DIRECTIONAL_COVERAGE
        if not coverage_ok: selected = []
        self._last_scan_diagnostics = {"status": "OK" if coverage_ok else "INSUFFICIENT_COVERAGE", "session": session_name, "trading_date": str(trading_date), "scan_window": scan_window, "preferred_window": "09:50-13:00 MSK", "preferred_window_active": preferred, "universe_total": len(universe), "stocks_total": sum(1 for x in universe if x.get("market_group") == "STOCK"), "analyzed": len(results), "coverage_ratio": round(coverage_ratio, 4), "coverage_percent": coverage_percent, "coverage_required_percent": round(self.MIN_DIRECTIONAL_COVERAGE * 100.0, 1), "coverage_ok": coverage_ok, "skipped_total": sum(len(v) for v in skipped.values()), "skip_reasons": {k: len(v) for k, v in skipped.items() if v}, "skip_samples": {k: v[:10] for k, v in skipped.items() if v}, "benchmark": benchmark_ticker, "benchmark_change_percent": benchmark_change, "daily_benchmark_available": daily_benchmark_available, "daily_benchmark_days": len(benchmark_daily), "daily_profiles_qualified": sum(1 for x in results if x.get("daily_qualified")), "liquidity_passed": sum(1 for x in results if x.get("liquidity_gate")), "liquidity_filtered": len(skipped["LOW_LIQUIDITY"]), "liquidity_min_money_per_minute": self.MIN_MONEY_PER_MINUTE, "liquidity_min_recent_money_per_minute": self.MIN_RECENT_MONEY_PER_MINUTE, "selected": len(selected), "long_candidate": next((x["spot_ticker"] for x in selected if x["selection_role"] == "LONG_CANDIDATE"), None), "short_candidate": next((x["spot_ticker"] for x in selected if x["selection_role"] == "SHORT_CANDIDATE"), None), "group_status": {g: ("AVAILABLE" if any(x.get("market_group") == g for x in universe) else "UNAVAILABLE") for g in ("STOCK", "GOLD", "OIL", "GAS", "USDRUB")}, "data_policy": "SPOT_BASE_ONLY_NO_FUTURES", "direction_policy": "COMPLETED_D1_STRUCTURE_PLUS_DAILY_RS_PLUS_INTRADAY_RS_PLUS_ABSOLUTE_LIQUIDITY_PLUS_FLOW"}
        return selected
