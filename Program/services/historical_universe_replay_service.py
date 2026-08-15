"""Trader_7_12 Pro - Historical Universe Morning Replay."""

from datetime import date, datetime, timedelta, timezone, time

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.futures_confirmation_service import FuturesConfirmationService
from services.history_candle_service import HistoryCandleService
from services.morning_radar_service import MorningRadarService
from services.morning_replay_service import MorningReplayService


class HistoricalUniverseReplayService:
    """Replay SPOT setup, market-relative strength and futures confirmation."""

    VERSION = "0.9"
    DEFAULT_MIN_MONEY = 100_000_000.0
    DEFAULT_AVERAGE_DAYS = 5
    MAX_CONTRACTS_PER_SPOT = 2
    MIN_DAYS_TO_EXPIRY = 3
    RS_LOOKBACK_DAYS = 3
    RS_TICKERS = ("IMOEX", "IMOEX2")

    def __init__(self, mapping_service=None, history_service=None, replay_service=None):
        self.mapping_service = mapping_service or FuturesSpotMappingService()
        self.history_service = history_service or HistoryCandleService()
        self.replay_service = replay_service or MorningReplayService(history_service=self.history_service)
        self.radar_helper = MorningRadarService()

    @staticmethod
    def _as_date(value):
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    @staticmethod
    def _parse_expiry(value):
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @classmethod
    def _expiry_is_usable(cls, trading_date, expiry):
        expiry = cls._parse_expiry(expiry)
        return expiry is not None and (expiry - trading_date).days > cls.MIN_DAYS_TO_EXPIRY

    def load_mappings_for_date(self, trading_date):
        trading_date = self._as_date(trading_date)
        mappings = self.mapping_service.load()
        if not isinstance(mappings, list):
            return []
        grouped = {}
        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            spot = str(mapping.get("spot_ticker") or "").strip().upper()
            expiry = self._parse_expiry(mapping.get("futures_expiry"))
            if not spot or not self._expiry_is_usable(trading_date, expiry):
                continue
            candidate = dict(mapping)
            candidate["futures_expiry"] = expiry.isoformat()
            grouped.setdefault(spot, []).append(candidate)
        selected = []
        for candidates in grouped.values():
            candidates.sort(key=lambda item: (
                self._parse_expiry(item.get("futures_expiry")) or date.max,
                str(item.get("futures_ticker") or ""),
            ))
            selected.extend(candidates[:self.MAX_CONTRACTS_PER_SPOT])
        return sorted(selected, key=lambda item: (
            str(item.get("spot_ticker") or ""),
            self._parse_expiry(item.get("futures_expiry")) or date.max,
            str(item.get("futures_ticker") or ""),
        ))

    def load_daily_candles(self, ticker, class_code, trading_date):
        trading_date = self._as_date(trading_date)
        end_moscow = datetime.combine(trading_date, datetime.min.time()).replace(tzinfo=self.history_service.MOSCOW_TZ)
        start_utc = end_moscow.astimezone(timezone.utc) - timedelta(days=12)
        end_utc = end_moscow.astimezone(timezone.utc)
        try:
            data = self.history_service.trade_service.api.get_candles(ticker, class_code, interval="D", start_time=start_utc, end_time=end_utc)
        except Exception as exc:
            print(f"Historical candles unavailable: {ticker}/{class_code}: {type(exc).__name__}")
            return []
        bars = data.get("bars", []) if isinstance(data, dict) else []
        result = []
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            candle_date = self.history_service.get_moscow_date(bar.get("time"))
            if candle_date is None or candle_date >= trading_date:
                continue
            try:
                close = float(bar.get("close") or 0)
                volume = float(bar.get("volume") or 0)
            except (TypeError, ValueError):
                continue
            if close <= 0:
                continue
            result.append({
                "time": bar.get("time"), "date": candle_date.isoformat(),
                "open": float(bar.get("open") or 0), "high": float(bar.get("high") or 0),
                "low": float(bar.get("low") or 0), "close": close, "volume": volume,
            })
        result.sort(key=lambda item: item["date"])
        return result

    @staticmethod
    def _instrument_ticker(item):
        if not isinstance(item, dict):
            return ""
        return str(
            item.get("ticker")
            or item.get("secCode")
            or item.get("securityCode")
            or ""
        ).strip().upper()

    @staticmethod
    def _instrument_class_code(item):
        if not isinstance(item, dict):
            return ""
        for key in ("classCode", "class_code", "boardClassCode"):
            value = item.get(key)
            if value:
                return str(value).strip()
        for board in item.get("boards") or []:
            if not isinstance(board, dict):
                continue
            for key in ("classCode", "class_code"):
                value = board.get(key)
                if value:
                    return str(value).strip()
        return ""

    def load_market_benchmark(self):
        """Resolve IMOEX/IMOEX2 dynamically from BCS index metadata.

        The historical replay must never guess a benchmark class code.  BCS
        documents INDICES as a valid instrument type, but some sessions may
        return an empty by-type result.  In that case retry resolution by the
        exact benchmark tickers through the API's ticker lookup when available.
        """
        api = self.history_service.trade_service.api
        instruments = []
        try:
            instruments = api.get_instruments("INDICES")
        except Exception as exc:
            print(f"Historical RS benchmark metadata error: {type(exc).__name__}")

        if not isinstance(instruments, list):
            instruments = []

        def resolve(records):
            for preferred in self.RS_TICKERS:
                for item in records:
                    if self._instrument_ticker(item) != preferred:
                        continue
                    class_code = self._instrument_class_code(item)
                    if class_code:
                        return {"ticker": preferred, "class_code": class_code, "source": "by-type"}
            return None

        resolved = resolve(instruments)
        if resolved:
            print(
                f"Historical RS benchmark: {resolved['ticker']}/{resolved['class_code']} "
                f"(dynamic INDICES metadata)"
            )
            return resolved

        lookup = getattr(api, "get_instruments_by_tickers", None)
        if callable(lookup):
            try:
                records = lookup(list(self.RS_TICKERS))
            except Exception as exc:
                print(f"Historical RS benchmark ticker lookup error: {type(exc).__name__}")
                records = []
            if isinstance(records, list):
                resolved = resolve(records)
                if resolved:
                    resolved["source"] = "by-tickers"
                    print(
                        f"Historical RS benchmark: {resolved['ticker']}/{resolved['class_code']} "
                        f"(dynamic ticker metadata)"
                    )
                    return resolved

        print("Historical RS benchmark: UNAVAILABLE — no IMOEX/IMOEX2 metadata resolved")
        return None

    def calculate_relative_strength(self, candles, benchmark_candles, benchmark_name=None):
        """Compare the same completed daily window against IMOEX/IMOEX2."""
        selected = candles[-self.RS_LOOKBACK_DAYS:]
        benchmark = benchmark_candles[-self.RS_LOOKBACK_DAYS:]
        if len(selected) < 2 or len(benchmark) < 2:
            return {"available": False, "score": 0.0, "asset_change_percent": 0.0, "market_change_percent": 0.0, "benchmark": benchmark_name}
        asset_change = (selected[-1]["close"] - selected[0]["close"]) / selected[0]["close"] * 100
        market_change = (benchmark[-1]["close"] - benchmark[0]["close"]) / benchmark[0]["close"] * 100
        excess = asset_change - market_change
        return {
            "available": True,
            "score": round(max(-50.0, min(50.0, excess * 10.0)), 2),
            "asset_change_percent": round(asset_change, 2),
            "market_change_percent": round(market_change, 2),
            "excess_change_percent": round(excess, 2),
            "benchmark": benchmark_name,
        }

    def historical_liquidity(self, candles, completed_days=None):
        completed_days = completed_days or self.DEFAULT_AVERAGE_DAYS
        selected = candles[-int(completed_days):]
        turnovers = [float(item.get("close", 0) or 0) * float(item.get("volume", 0) or 0) for item in selected]
        turnovers = [value for value in turnovers if value > 0]
        return sum(turnovers) / len(turnovers) if turnovers else 0.0

    def prepare_futures_candidates(self, candidates, trading_date):
        trading_date = self._as_date(trading_date)
        ranked = []
        for candidate in candidates:
            if not self._expiry_is_usable(trading_date, candidate.get("futures_expiry")):
                continue
            ticker = str(candidate.get("futures_ticker") or "").strip().upper()
            class_code = str(candidate.get("futures_class_code") or "").strip()
            if not ticker or not class_code:
                continue
            liquidity = self.historical_liquidity(self.load_daily_candles(ticker, class_code, trading_date))
            if liquidity <= 0:
                continue
            selected = dict(candidate)
            selected["futures_average_daily_money"] = liquidity
            ranked.append(selected)
        ranked.sort(key=lambda item: (float(item.get("futures_average_daily_money", 0) or 0), str(item.get("futures_ticker") or "")), reverse=True)
        return ranked

    def select_futures_for_spot(self, candidates, trading_date):
        ranked = self.prepare_futures_candidates(candidates, trading_date)
        return ranked[0] if ranked else None

    def load_futures_candles(self, ticker, class_code, trading_date, end_time):
        trading_date = self._as_date(trading_date)
        if isinstance(end_time, str):
            end_time = time.fromisoformat(end_time[:8])
        start_moscow = datetime.combine(trading_date, time(7, 0), tzinfo=self.replay_service.MOSCOW_TZ)
        end_moscow = datetime.combine(trading_date, end_time, tzinfo=self.replay_service.MOSCOW_TZ)
        if end_moscow < start_moscow:
            return []
        try:
            data = self.history_service.trade_service.api.get_candles(ticker, class_code, interval="M5", start_time=start_moscow.astimezone(timezone.utc), end_time=end_moscow.astimezone(timezone.utc))
        except Exception:
            return []
        bars = data.get("bars", []) if isinstance(data, dict) else []
        result = []
        for bar in bars:
            if not isinstance(bar, dict):
                continue
            try:
                open_price = float(bar.get("open") or 0)
                close_price = float(bar.get("close") or 0)
                volume = float(bar.get("volume") or 0)
            except (TypeError, ValueError):
                continue
            if open_price <= 0 or close_price <= 0:
                continue
            dt = self.history_service.to_moscow(bar.get("time"))
            if dt is None or dt.date() != trading_date or dt.time() < time(7, 0) or dt.time() > end_time:
                continue
            result.append({"time": bar.get("time"), "open": open_price, "high": float(bar.get("high") or 0), "low": float(bar.get("low") or 0), "close": close_price, "volume": volume})
        result.sort(key=lambda item: str(item.get("time") or ""))
        return result

    def confirm_futures_at_checkpoint(self, ticker, class_code, direction, trading_date, checkpoint):
        candles = self.load_futures_candles(ticker, class_code, trading_date, checkpoint)
        return FuturesConfirmationService.analyze_candles(candles, direction)

    def evaluate_futures_candidate(self, candidate, direction, trading_date, replay):
        ticker = str(candidate.get("futures_ticker") or "").strip().upper()
        class_code = str(candidate.get("futures_class_code") or "").strip()
        timeline = []
        first_ready = None
        first_confirmed = None
        for item in replay:
            if str(item.get("setup_state") or "WAIT").upper() != "READY":
                continue
            checkpoint = item.get("checkpoint")
            if first_ready is None:
                first_ready = checkpoint
            confirmation = self.confirm_futures_at_checkpoint(ticker, class_code, direction, trading_date, checkpoint)
            timeline.append({"checkpoint": checkpoint, "setup": item.get("setup", "NONE"), "setup_state": item.get("setup_state", "WAIT"), "confirmation": confirmation})
            if first_confirmed is None and confirmation.get("status") == "OK":
                first_confirmed = {"checkpoint": checkpoint, "confirmation": confirmation, "setup": item.get("setup", "NONE"), "setup_state": item.get("setup_state", "WAIT"), "entry_trigger": item.get("entry_trigger", 0.0), "previous_high": item.get("previous_high", 0.0), "previous_low": item.get("previous_low", 0.0)}
                break
        return {"candidate": candidate, "ready_time": first_ready, "confirmation_time": first_confirmed.get("checkpoint") if first_confirmed else None, "futures_confirmation": first_confirmed.get("confirmation") if first_confirmed else None, "setup": first_confirmed.get("setup", "NONE") if first_confirmed else "NONE", "setup_state": first_confirmed.get("setup_state", "WAIT") if first_confirmed else "WAIT", "entry_trigger": first_confirmed.get("entry_trigger", 0.0) if first_confirmed else 0.0, "previous_high": first_confirmed.get("previous_high", 0.0) if first_confirmed else 0.0, "previous_low": first_confirmed.get("previous_low", 0.0) if first_confirmed else 0.0, "futures_price": float((first_confirmed.get("confirmation") or {}).get("last_price", 0) or 0) if first_confirmed else 0.0, "futures_confirmation_timeline": timeline}

    def _candidate_rank(self, evaluation):
        confirmation_time = evaluation.get("confirmation_time")
        ready_time = evaluation.get("ready_time")
        confirmation = evaluation.get("futures_confirmation") or {}
        candidate = evaluation.get("candidate") or {}
        return (confirmation_time is not None, confirmation_time or "99:99", ready_time is not None, ready_time or "99:99", confirmation.get("score", 0), float(candidate.get("futures_average_daily_money", 0) or 0))

    def replay(self, trading_date, min_money=None, checkpoints=None, limit=None):
        trading_date = self._as_date(trading_date)
        min_money = self.DEFAULT_MIN_MONEY if min_money is None else float(min_money)
        benchmark_meta = self.load_market_benchmark()
        benchmark_candles = self.load_daily_candles(benchmark_meta["ticker"], benchmark_meta["class_code"], trading_date) if benchmark_meta else []
        if benchmark_meta and len(benchmark_candles) < 2:
            print(
                f"Historical RS benchmark candles: UNAVAILABLE — "
                f"{benchmark_meta['ticker']}/{benchmark_meta['class_code']} returned "
                f"{len(benchmark_candles)} completed daily candles"
            )
            benchmark_meta = None
            benchmark_candles = []
        elif benchmark_meta:
            print(
                f"Historical RS benchmark candles: {len(benchmark_candles)} completed daily candles "
                f"for {benchmark_meta['ticker']}/{benchmark_meta['class_code']}"
            )
        mappings = self.load_mappings_for_date(trading_date)
        rows = []
        grouped = {}
        for mapping in mappings:
            spot = str(mapping.get("spot_ticker") or "").strip().upper()
            if spot:
                grouped.setdefault(spot, []).append(mapping)
        for candidates in grouped.values():
            prepared = self.prepare_futures_candidates(candidates, trading_date)
            if not prepared:
                continue
            spot = str(prepared[0].get("spot_ticker") or "").strip().upper()
            spot_class = str(prepared[0].get("spot_class_code") or "").strip()
            if not spot or not spot_class:
                continue
            daily = self.load_daily_candles(spot, spot_class, trading_date)
            if len(daily) < 3:
                continue
            avg_money = self.historical_liquidity(daily)
            if avg_money < min_money:
                continue
            trend = self.radar_helper.calculate_daily_trend(daily)
            direction = trend.get("direction")
            if direction not in {"LONG", "SHORT"}:
                continue
            relative_strength = self.calculate_relative_strength(daily, benchmark_candles, benchmark_meta["ticker"] if benchmark_meta else None)
            replay = self.replay_service.replay_setup(ticker=spot, class_code=spot_class, direction=direction, trading_date=trading_date, checkpoints=checkpoints)
            evaluations = [self.evaluate_futures_candidate(candidate, direction, trading_date, replay) for candidate in prepared]
            evaluations.sort(key=self._candidate_rank, reverse=True)
            best = evaluations[0]
            mapping = best["candidate"]
            confirmation = best.get("futures_confirmation") or {}
            setup_seen = next((item for item in replay if item.get("setup") != "NONE"), None)
            rows.append({
                "futures_ticker": mapping.get("futures_ticker"), "futures_class_code": mapping.get("futures_class_code"), "futures_expiry": mapping.get("futures_expiry"), "futures_average_daily_money": mapping.get("futures_average_daily_money", 0.0), "futures_candidates_evaluated": len(evaluations),
                "spot_ticker": spot, "spot_class_code": spot_class, "direction": direction, "trend_state": trend.get("state"), "trend_change_percent": trend.get("change_percent", 0.0), "average_daily_money": avg_money,
                "relative_strength": relative_strength.get("score", 0.0), "relative_strength_data": relative_strength, "relative_strength_available": relative_strength.get("available", False),
                "setup_first_seen": setup_seen.get("checkpoint") if setup_seen else None, "ready_time": best.get("ready_time"), "confirmation_time": best.get("confirmation_time"), "trade_ready_time": best.get("confirmation_time"), "futures_price": best.get("futures_price", 0.0), "setup": best.get("setup", "NONE"), "setup_state": best.get("setup_state", "WAIT"), "entry_trigger": best.get("entry_trigger", 0.0), "previous_high": best.get("previous_high", 0.0), "previous_low": best.get("previous_low", 0.0), "futures_confirmation": confirmation, "futures_confirmation_timeline": best.get("futures_confirmation_timeline", []), "replay": replay,
            })
        rows.sort(key=lambda item: (item.get("trade_ready_time") is not None, item.get("trade_ready_time") or "99:99", item.get("ready_time") is not None, item.get("ready_time") or "99:99", item.get("average_daily_money", 0)), reverse=True)
        if limit is not None:
            rows = rows[:int(limit)]
        return rows

    @staticmethod
    def print_results(rows, trading_date, min_money):
        print()
        print("=" * 128)
        print("TRADER_7_12 PRO — HISTORICAL TOP CANDIDATES")
        print(f"DATE: {trading_date} | READ ONLY — NO ORDERS")
        print("=" * 128)
        print(f"{'#':>3} {'FUTURES':<8} {'SPOT':<7} {'DIR':<6} {'SCORE':>7} {'SETUP':<10} {'READY':<6} {'CONF':<6} {'RS':>7} {'SPOT MONEY':>15} {'FUT MONEY':>15}")
        print("-" * 128)
        for rank, item in enumerate(rows, start=1):
            confirmation = item.get("futures_confirmation") or {}
            print(f"{rank:>3} {str(item.get('futures_ticker', '-')):<8} {str(item.get('spot_ticker', '-')):<7} {str(item.get('direction', '-')):<6} {float(item.get('candidate_score', 0) or 0):>7.2f} {str(item.get('setup', '-')):<10} {str(item.get('ready_time', '-')):<6} {str(item.get('confirmation_time', '-')):<6} {float(item.get('relative_strength', 0) or 0):>7.2f}{float(item.get('average_daily_money', 0) or 0):>15,.0f} {float(item.get('futures_average_daily_money', 0) or 0):>15,.0f}")
        print("=" * 128)
        print(f"CANDIDATES AFTER LIQUIDITY FILTER: {len(rows)}")
        print("Historical RS is calculated against the dynamically resolved IMOEX/IMOEX2 benchmark using completed daily candles only.")
        print("Risk sizing, deposit, SL/TP, position sizing and order execution are not used.")
        print("=" * 128)
