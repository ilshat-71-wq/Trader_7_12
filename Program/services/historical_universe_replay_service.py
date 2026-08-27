"""Trader_7_12 Pro - Historical SPOT-first morning replay."""

from datetime import date, datetime, timedelta, timezone, time

from services.futures_confirmation_service import FuturesConfirmationService
from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.history_candle_service import HistoryCandleService
from services.morning_radar_service import MorningRadarService
from services.morning_replay_service import MorningReplayService
from services.spot_signal_contract import lifecycle_state
from services.spot_universe_service import SpotUniverseService


class HistoricalUniverseReplayService:
    """Replay the canonical SPOT pipeline; futures are secondary outcome data."""

    VERSION = "1.1"
    DEFAULT_MIN_MONEY = 100_000_000.0
    DEFAULT_AVERAGE_DAYS = 5
    MAX_CONTRACTS_PER_SPOT = 2
    MIN_DAYS_TO_EXPIRY = 3
    RS_LOOKBACK_DAYS = 3
    RS_TICKERS = ("IMOEX2", "IRUS2")

    def __init__(self, mapping_service=None, history_service=None, replay_service=None, radar_helper=None, spot_universe_service=None):
        self.mapping_service = mapping_service or FuturesSpotMappingService()
        self.spot_universe_service = spot_universe_service or SpotUniverseService()
        self.history_service = history_service or HistoryCandleService()
        self.replay_service = replay_service or MorningReplayService(history_service=self.history_service)
        self.radar_helper = radar_helper or MorningRadarService()

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
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

    def load_spot_universe(self):
        """Return the independent SPOT universe; futures mapping is not consulted."""
        spots = self.spot_universe_service.load()
        if not isinstance(spots, list):
            return []
        result, seen = [], set()
        for spot in spots:
            if not isinstance(spot, dict):
                continue
            ticker = str(spot.get("spot_ticker") or spot.get("ticker") or "").strip().upper()
            class_code = str(spot.get("spot_class_code") or spot.get("class_code") or spot.get("classCode") or "").strip()
            if not ticker or not class_code or (ticker, class_code) in seen:
                continue
            seen.add((ticker, class_code))
            result.append({
                "spot_ticker": ticker,
                "spot_class_code": class_code,
                "spot_group": spot.get("spot_group"),
                "spot_universe": spot.get("spot_universe", "DYNAMIC_SPOT"),
            })
        return sorted(result, key=lambda item: (item["spot_ticker"], item["spot_class_code"]))

    def load_mappings_for_date(self, trading_date):
        """Load futures references only for post-SPOT mapping/outcome analysis."""
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
            item = dict(mapping)
            item["futures_expiry"] = expiry.isoformat()
            item["days_to_expiry"] = (expiry - trading_date).days
            grouped.setdefault(spot, []).append(item)
        selected = []
        for candidates in grouped.values():
            candidates.sort(key=lambda item: (self._parse_expiry(item.get("futures_expiry")) or date.max, str(item.get("futures_ticker") or "")))
            selected.extend(candidates[:self.MAX_CONTRACTS_PER_SPOT])
        return selected

    def load_daily_candles(self, ticker, class_code, trading_date):
        trading_date = self._as_date(trading_date)
        end_moscow = datetime.combine(trading_date, datetime.min.time()).replace(tzinfo=self.history_service.MOSCOW_TZ)
        try:
            data = self.history_service.trade_service.api.get_candles(
                ticker, class_code, interval="D",
                start_time=(end_moscow.astimezone(timezone.utc) - timedelta(days=12)),
                end_time=end_moscow.astimezone(timezone.utc),
            )
        except Exception as exc:
            print(f"Historical candles unavailable: {ticker}/{class_code}: {type(exc).__name__}")
            return []
        result = []
        for bar in (data.get("bars", []) if isinstance(data, dict) else []):
            if not isinstance(bar, dict):
                continue
            candle_date = self.history_service.get_moscow_date(bar.get("time"))
            if candle_date is None or candle_date >= trading_date:
                continue
            try:
                close, volume = float(bar.get("close") or 0), float(bar.get("volume") or 0)
            except (TypeError, ValueError):
                continue
            if close <= 0:
                continue
            result.append({"time": bar.get("time"), "date": candle_date.isoformat(), "open": float(bar.get("open") or 0), "high": float(bar.get("high") or 0), "low": float(bar.get("low") or 0), "close": close, "volume": volume})
        return sorted(result, key=lambda item: item["date"])

    @staticmethod
    def _instrument_ticker(item):
        return str(item.get("ticker") or item.get("secCode") or item.get("securityCode") or "").strip().upper() if isinstance(item, dict) else ""

    @staticmethod
    def _instrument_class_code(item):
        if not isinstance(item, dict):
            return ""
        for key in ("classCode", "class_code", "boardClassCode"):
            if item.get(key):
                return str(item[key]).strip()
        for board in item.get("boards") or []:
            if isinstance(board, dict) and (board.get("classCode") or board.get("class_code")):
                return str(board.get("classCode") or board.get("class_code")).strip()
        return ""

    def load_market_benchmark(self):
        """Resolve IMOEX2/IRUS2 dynamically; never guess benchmark metadata."""
        api = self.history_service.trade_service.api
        try:
            instruments = api.get_instruments("INDICES")
        except Exception as exc:
            print(f"Historical RS benchmark metadata error: {type(exc).__name__}")
            instruments = []
        if not isinstance(instruments, list):
            instruments = []
        def resolve(records):
            for preferred in self.RS_TICKERS:
                for item in records:
                    if self._instrument_ticker(item) == preferred:
                        code = self._instrument_class_code(item)
                        if code:
                            return {"ticker": preferred, "class_code": code, "source": "metadata"}
            return None
        resolved = resolve(instruments)
        if resolved:
            return resolved
        lookup = getattr(api, "get_instruments_by_tickers", None)
        if callable(lookup):
            try:
                resolved = resolve(lookup(list(self.RS_TICKERS)))
            except Exception:
                resolved = None
            if resolved:
                resolved["source"] = "ticker_lookup"
                return resolved
        return None

    def calculate_relative_strength(self, candles, benchmark_candles, benchmark_name=None):
        selected, benchmark = candles[-self.RS_LOOKBACK_DAYS:], benchmark_candles[-self.RS_LOOKBACK_DAYS:]
        if len(selected) < 2 or len(benchmark) < 2:
            return {"available": False, "score": 0.0, "asset_change_percent": 0.0, "market_change_percent": 0.0, "benchmark": benchmark_name}
        asset_change = (selected[-1]["close"] - selected[0]["close"]) / selected[0]["close"] * 100
        market_change = (benchmark[-1]["close"] - benchmark[0]["close"]) / benchmark[0]["close"] * 100
        excess = asset_change - market_change
        return {"available": True, "score": round(max(-50.0, min(50.0, excess * 10.0)), 2), "asset_change_percent": round(asset_change, 2), "market_change_percent": round(market_change, 2), "excess_change_percent": round(excess, 2), "benchmark": benchmark_name}

    def historical_liquidity(self, candles, completed_days=None):
        selected = candles[-int(completed_days or self.DEFAULT_AVERAGE_DAYS):]
        turnovers = [float(item.get("close", 0) or 0) * float(item.get("volume", 0) or 0) for item in selected]
        turnovers = [value for value in turnovers if value > 0]
        return sum(turnovers) / len(turnovers) if turnovers else 0.0

    def load_futures_candles(self, ticker, class_code, trading_date, end_time):
        trading_date = self._as_date(trading_date)
        if isinstance(end_time, str):
            end_time = time.fromisoformat(end_time[:8])
        start = datetime.combine(trading_date, time(7, 0), tzinfo=self.replay_service.MOSCOW_TZ)
        end = datetime.combine(trading_date, end_time, tzinfo=self.replay_service.MOSCOW_TZ)
        if end < start:
            return []
        try:
            data = self.history_service.trade_service.api.get_candles(ticker, class_code, interval="M5", start_time=start.astimezone(timezone.utc), end_time=end.astimezone(timezone.utc))
        except Exception:
            return []
        result = []
        for bar in (data.get("bars", []) if isinstance(data, dict) else []):
            if not isinstance(bar, dict):
                continue
            dt = self.history_service.to_moscow(bar.get("time"))
            if dt is None or dt.date() != trading_date or dt.time() < time(7, 0) or dt.time() > end_time:
                continue
            try:
                op, cl = float(bar.get("open") or 0), float(bar.get("close") or 0)
            except (TypeError, ValueError):
                continue
            if op <= 0 or cl <= 0:
                continue
            result.append({"time": bar.get("time"), "open": op, "high": float(bar.get("high") or 0), "low": float(bar.get("low") or 0), "close": cl, "volume": float(bar.get("volume") or 0)})
        return sorted(result, key=lambda item: str(item.get("time") or ""))

    def confirm_futures_at_checkpoint(self, ticker, class_code, direction, trading_date, checkpoint):
        return FuturesConfirmationService.analyze_candles(self.load_futures_candles(ticker, class_code, trading_date, checkpoint), direction)

    @staticmethod
    def confirmation_window(value):
        if not value:
            return "NONE"
        try:
            p = str(value)[:8].split(":")
            seconds = int(p[0]) * 3600 + int(p[1]) * 60 + int(p[2] if len(p) > 2 else 0)
        except (TypeError, ValueError, IndexError):
            return "NONE"
        if 7 * 3600 <= seconds < 10 * 3600:
            return "EARLY"
        if 10 * 3600 <= seconds <= 13 * 3600:
            return "LATE"
        return "NONE"

    @staticmethod
    def _canonical_lifecycle(replay):
        """Decorate historical checkpoints with the canonical SPOT lifecycle only."""
        if not isinstance(replay, list):
            return []
        decorated = []
        previous_price = None
        previous_state = None
        for raw in replay:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            try:
                spot_price = float(item.get("spot_price", item.get("close", 0)) or 0)
            except (TypeError, ValueError):
                spot_price = 0.0
            lifecycle = lifecycle_state(
                setup_state=item.get("setup_state", "WAIT"),
                direction=item.get("direction"),
                setup=item.get("setup", "NONE"),
                entry_trigger=item.get("entry_trigger", 0),
                spot_price=spot_price,
                previous_price=previous_price,
                prior_signal_state=previous_state,
                consecutive_active=1,
                min_active_observations=1,
                invalidation_level=item.get("invalidation_level"),
                new_setup=bool(item.get("new_setup", False)),
            )
            item.update(lifecycle)
            item["spot_price"] = spot_price
            decorated.append(item)
            previous_price = spot_price if spot_price > 0 else previous_price
            previous_state = lifecycle.get("signal_state")
        return decorated

    @classmethod
    def _spot_trigger_active(cls, item):
        """Compatibility projection backed by the canonical SPOT lifecycle contract."""
        if not isinstance(item, dict):
            return False
        return bool(cls._canonical_lifecycle([item])[0].get("trigger_active")) if item else False

    @classmethod
    def _first_ready(cls, replay):
        """First historical checkpoint whose canonical SPOT lifecycle is READY/CONFIRMED."""
        for item in cls._canonical_lifecycle(replay):
            if item.get("signal_state") in {"READY", "CONFIRMED"} and item.get("trigger_active"):
                return item
        return None

    def replay(self, trading_date, min_money=None, checkpoints=None, limit=None):
        """Run historical SPOT eligibility/ranking inputs before any futures lookup."""
        trading_date = self._as_date(trading_date)
        min_money = self.DEFAULT_MIN_MONEY if min_money is None else float(min_money)
        benchmark_meta = self.load_market_benchmark()
        benchmark_candles = self.load_daily_candles(benchmark_meta["ticker"], benchmark_meta["class_code"], trading_date) if benchmark_meta else []
        if len(benchmark_candles) < 2:
            benchmark_meta, benchmark_candles = None, []

        rows = []
        for spot in self.load_spot_universe():
            ticker, class_code = spot["spot_ticker"], spot["spot_class_code"]
            daily = self.load_daily_candles(ticker, class_code, trading_date)
            if len(daily) < 3:
                continue
            avg_money = self.historical_liquidity(daily)
            if avg_money < min_money:
                continue
            trend = self.radar_helper.calculate_daily_trend(daily)
            direction = trend.get("direction")
            if direction not in {"LONG", "SHORT"}:
                continue
            rs = self.calculate_relative_strength(daily, benchmark_candles, benchmark_meta["ticker"] if benchmark_meta else None)
            replay = self._canonical_lifecycle(self.replay_service.replay_setup(ticker=ticker, class_code=class_code, direction=direction, trading_date=trading_date, checkpoints=checkpoints))
            ready = next((item for item in replay if item.get("signal_state") in {"READY", "CONFIRMED"} and item.get("trigger_active")), None)
            selected = ready or (replay[-1] if replay else {})
            rows.append({
                "futures_ticker": "", "futures_class_code": "", "futures_expiry": None, "days_to_expiry": None,
                "futures_average_daily_money": 0.0, "futures_candidates_evaluated": 0,
                "spot_ticker": ticker, "spot_class_code": class_code, "spot_group": spot.get("spot_group"), "spot_universe": spot.get("spot_universe"),
                "direction": direction, "trend_state": trend.get("state"), "trend_change_percent": trend.get("change_percent", 0.0), "average_daily_money": avg_money,
                "relative_strength": rs.get("score", 0.0), "relative_strength_data": rs, "relative_strength_available": rs.get("available", False),
                "setup_first_seen": next((item.get("checkpoint") for item in replay if item.get("setup") != "NONE"), None),
                "ready_time": ready.get("checkpoint") if ready else None, "trade_ready_time": ready.get("checkpoint") if ready else None,
                "confirmation_time": None, "futures_price": 0.0, "setup": selected.get("setup", "NONE"), "setup_state": selected.get("setup_state", "WAIT"),
                "entry_trigger": float(selected.get("entry_trigger", 0) or 0), "previous_high": float(selected.get("previous_high", 0) or 0), "previous_low": float(selected.get("previous_low", 0) or 0),
                "spot_price": float(selected.get("spot_price", selected.get("close", 0)) or 0),
                "trigger_active": bool(selected.get("trigger_active", False)),
                "signal_state": selected.get("signal_state", "WAIT"), "trigger_state": selected.get("trigger_state", "WAITING"),
                "signal_state_reason": selected.get("signal_state_reason", ""),
                "futures_confirmation": {}, "futures_confirmation_timeline": [], "replay": replay,
                "readiness_source": "SPOT", "readiness_confirmed_by_futures": False,
            })
        return rows[:int(limit)] if limit is not None else rows

    def attach_futures_context(self, rows, trading_date):
        """Attach optional futures mapping after SPOT ranking; never change SPOT evidence."""
        mappings = self.load_mappings_for_date(trading_date)
        by_spot = {}
        for mapping in mappings:
            by_spot.setdefault(str(mapping.get("spot_ticker") or "").strip().upper(), []).append(mapping)
        result = []
        for row in rows or []:
            item = dict(row)
            candidates = by_spot.get(str(item.get("spot_ticker") or "").strip().upper(), [])
            mapping = candidates[0] if candidates else None
            if mapping:
                item.update({"futures_ticker": mapping.get("futures_ticker", ""), "futures_class_code": mapping.get("futures_class_code", ""), "futures_expiry": mapping.get("futures_expiry"), "days_to_expiry": mapping.get("days_to_expiry"), "futures_mapping_source": "POST_SPOT_RANKING"})
            else:
                item["futures_mapping_source"] = "UNAVAILABLE_AFTER_SPOT_RANKING"
            result.append(item)
        return result
