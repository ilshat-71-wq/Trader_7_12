"""Trader_7_12 Pro - Historical Universe Morning Replay."""

from datetime import date, datetime, timedelta, timezone, time

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.futures_confirmation_service import FuturesConfirmationService
from services.history_candle_service import HistoryCandleService
from services.morning_radar_service import MorningRadarService
from services.morning_replay_service import MorningReplayService


class HistoricalUniverseReplayService:
    """Replay the SPOT setup and futures confirmation without future data."""

    VERSION = "0.7"
    DEFAULT_MIN_MONEY = 100_000_000.0
    DEFAULT_AVERAGE_DAYS = 5
    MAX_CONTRACTS_PER_SPOT = 2
    MIN_DAYS_TO_EXPIRY = 3

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
        end_moscow = datetime.combine(trading_date, datetime.min.time()).replace(
            tzinfo=self.history_service.MOSCOW_TZ
        )
        start_utc = end_moscow.astimezone(timezone.utc) - timedelta(days=12)
        end_utc = end_moscow.astimezone(timezone.utc)
        try:
            data = self.history_service.trade_service.api.get_candles(
                ticker, class_code, interval="D", start_time=start_utc, end_time=end_utc
            )
        except Exception:
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

    def historical_liquidity(self, candles, completed_days=None):
        completed_days = completed_days or self.DEFAULT_AVERAGE_DAYS
        selected = candles[-int(completed_days):]
        if not selected:
            return 0.0
        turnovers = [
            float(item.get("close", 0) or 0) * float(item.get("volume", 0) or 0)
            for item in selected
        ]
        turnovers = [value for value in turnovers if value > 0]
        return sum(turnovers) / len(turnovers) if turnovers else 0.0

    def prepare_futures_candidates(self, candidates, trading_date):
        """Keep eligible futures candidates and attach historical liquidity."""
        trading_date = self._as_date(trading_date)
        ranked = []
        for candidate in candidates:
            if not self._expiry_is_usable(trading_date, candidate.get("futures_expiry")):
                continue
            ticker = str(candidate.get("futures_ticker") or "").strip().upper()
            class_code = str(candidate.get("futures_class_code") or "").strip()
            if not ticker or not class_code:
                continue
            liquidity = self.historical_liquidity(
                self.load_daily_candles(ticker, class_code, trading_date)
            )
            if liquidity <= 0:
                continue
            selected = dict(candidate)
            selected["futures_average_daily_money"] = liquidity
            ranked.append(selected)
        ranked.sort(key=lambda item: (
            float(item.get("futures_average_daily_money", 0) or 0),
            str(item.get("futures_ticker") or ""),
        ), reverse=True)
        return ranked

    def select_futures_for_spot(self, candidates, trading_date):
        """Return the most liquid eligible contract as a compatibility helper."""
        ranked = self.prepare_futures_candidates(candidates, trading_date)
        return ranked[0] if ranked else None

    def load_futures_candles(self, ticker, class_code, trading_date, end_time):
        """Load only M5 futures candles available through the replay checkpoint."""
        trading_date = self._as_date(trading_date)
        if isinstance(end_time, str):
            end_time = time.fromisoformat(end_time[:8])
        start_moscow = datetime.combine(
            trading_date, time(7, 0), tzinfo=self.replay_service.MOSCOW_TZ
        )
        end_moscow = datetime.combine(
            trading_date, end_time, tzinfo=self.replay_service.MOSCOW_TZ
        )
        if end_moscow < start_moscow:
            return []
        try:
            data = self.history_service.trade_service.api.get_candles(
                ticker,
                class_code,
                interval="M5",
                start_time=start_moscow.astimezone(timezone.utc),
                end_time=end_moscow.astimezone(timezone.utc),
            )
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
            if (
                dt is None
                or dt.date() != trading_date
                or dt.time() < time(7, 0)
                or dt.time() > end_time
            ):
                continue
            result.append({
                "time": bar.get("time"),
                "open": open_price,
                "high": float(bar.get("high") or 0),
                "low": float(bar.get("low") or 0),
                "close": close_price,
                "volume": volume,
            })
        result.sort(key=lambda item: str(item.get("time") or ""))
        return result

    def confirm_futures_at_checkpoint(
        self, ticker, class_code, direction, trading_date, checkpoint
    ):
        """Confirm historical futures direction from M5 candles only."""
        candles = self.load_futures_candles(
            ticker, class_code, trading_date, checkpoint
        )
        return FuturesConfirmationService.analyze_candles(candles, direction)

    def evaluate_futures_candidate(
        self, candidate, direction, trading_date, replay
    ):
        """Evaluate futures causally at every SPOT READY checkpoint."""
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

            confirmation = self.confirm_futures_at_checkpoint(
                ticker, class_code, direction, trading_date, checkpoint
            )
            timeline.append({
                "checkpoint": checkpoint,
                "setup": item.get("setup", "NONE"),
                "setup_state": item.get("setup_state", "WAIT"),
                "confirmation": confirmation,
            })

            if first_confirmed is None and confirmation.get("status") == "OK":
                first_confirmed = {
                    "checkpoint": checkpoint,
                    "confirmation": confirmation,
                    "setup": item.get("setup", "NONE"),
                    "setup_state": item.get("setup_state", "WAIT"),
                    "entry_trigger": item.get("entry_trigger", 0.0),
                    "previous_high": item.get("previous_high", 0.0),
                    "previous_low": item.get("previous_low", 0.0),
                }
                break

        return {
            "candidate": candidate,
            "ready_time": first_ready,
            "confirmation_time": (
                first_confirmed.get("checkpoint") if first_confirmed else None
            ),
            "futures_confirmation": (
                first_confirmed.get("confirmation") if first_confirmed else None
            ),
            "setup": first_confirmed.get("setup", "NONE") if first_confirmed else "NONE",
            "setup_state": first_confirmed.get("setup_state", "WAIT") if first_confirmed else "WAIT",
            "entry_trigger": first_confirmed.get("entry_trigger", 0.0) if first_confirmed else 0.0,
            "previous_high": first_confirmed.get("previous_high", 0.0) if first_confirmed else 0.0,
            "previous_low": first_confirmed.get("previous_low", 0.0) if first_confirmed else 0.0,
            "futures_price": (
                float((first_confirmed.get("confirmation") or {}).get("last_price", 0) or 0)
                if first_confirmed else 0.0
            ),
            "futures_confirmation_timeline": timeline,
        }

    @staticmethod
    def _candidate_rank(evaluation):
        """Prefer confirmed contracts, then earliest confirmation, then liquidity."""
        confirmation_time = evaluation.get("confirmation_time")
        ready_time = evaluation.get("ready_time")
        confirmation = evaluation.get("futures_confirmation") or {}
        candidate = evaluation.get("candidate") or {}
        return (
            confirmation_time is not None,
            confirmation_time or "99:99",
            ready_time is not None,
            ready_time or "99:99",
            confirmation.get("score", 0),
            float(candidate.get("futures_average_daily_money", 0) or 0),
        )

    def replay(self, trading_date, min_money=None, checkpoints=None, limit=None):
        trading_date = self._as_date(trading_date)
        min_money = self.DEFAULT_MIN_MONEY if min_money is None else float(min_money)
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

            replay = self.replay_service.replay_setup(
                ticker=spot,
                class_code=spot_class,
                direction=direction,
                trading_date=trading_date,
                checkpoints=checkpoints,
            )

            evaluations = [
                self.evaluate_futures_candidate(
                    candidate, direction, trading_date, replay
                )
                for candidate in prepared
            ]
            evaluations.sort(key=self._candidate_rank, reverse=True)
            best = evaluations[0]
            mapping = best["candidate"]
            confirmation = best.get("futures_confirmation") or {}
            setup_seen = next(
                (item for item in replay if item.get("setup") != "NONE"),
                None,
            )

            rows.append({
                "futures_ticker": mapping.get("futures_ticker"),
                "futures_class_code": mapping.get("futures_class_code"),
                "futures_expiry": mapping.get("futures_expiry"),
                "futures_average_daily_money": mapping.get(
                    "futures_average_daily_money", 0.0
                ),
                "futures_candidates_evaluated": len(evaluations),
                "spot_ticker": spot,
                "spot_class_code": spot_class,
                "direction": direction,
                "trend_state": trend.get("state"),
                "trend_change_percent": trend.get("change_percent", 0.0),
                "average_daily_money": avg_money,
                "setup_first_seen": setup_seen.get("checkpoint") if setup_seen else None,
                "ready_time": best.get("ready_time"),
                "confirmation_time": best.get("confirmation_time"),
                "trade_ready_time": best.get("confirmation_time"),
                "futures_price": best.get("futures_price", 0.0),
                "setup": best.get("setup", "NONE"),
                "setup_state": best.get("setup_state", "WAIT"),
                "entry_trigger": best.get("entry_trigger", 0.0),
                "previous_high": best.get("previous_high", 0.0),
                "previous_low": best.get("previous_low", 0.0),
                "futures_confirmation": confirmation,
                "futures_confirmation_timeline": best.get(
                    "futures_confirmation_timeline", []
                ),
                "replay": replay,
            })

        rows.sort(key=lambda item: (
            item.get("trade_ready_time") is not None,
            item.get("trade_ready_time") or "99:99",
            item.get("ready_time") is not None,
            item.get("ready_time") or "99:99",
            item.get("average_daily_money", 0),
        ), reverse=True)
        if limit is not None:
            rows = rows[:int(limit)]
        return rows

    @staticmethod
    def print_results(rows, trading_date, min_money):
        print()
        print("=" * 140)
        print("TRADER_7_12 PRO - DYNAMIC HISTORICAL MORNING REPLAY")
        print("READ ONLY — NO ORDERS")
        print(f"DATE: {trading_date} | MIN AVG DAILY MONEY: {min_money:,.0f}")
        print("=" * 140)
        print(
            f"{'FUTURES':<12}{'SPOT':<9}{'DIR':<7}{'READY':<9}"
            f"{'CONF':<9}{'TRADE':<9}{'TRADES':>8}{'MONEY':>16}{'TRIGGER':>14}"
        )
        print("-" * 140)
        for row in rows:
            confirmation = row.get("futures_confirmation") or {}
            print(
                f"{str(row['futures_ticker'] or '-'): <12}"
                f"{row['spot_ticker']:<9}"
                f"{row['direction']:<7}"
                f"{str(row.get('ready_time') or '-'):>9}"
                f"{str(row.get('confirmation_time') or '-'):>9}"
                f"{str(row.get('trade_ready_time') or '-'):>9}"
                f"{int(confirmation.get('trade_count', 0) or 0):>8}"
                f"{float(confirmation.get('money_volume', 0) or 0):>16,.0f}"
                f"{float(row['entry_trigger'] or 0):>14.4f}"
            )
        print("-" * 140)
        print(f"READY SETUPS: {sum(row['ready_time'] is not None for row in rows)}")
        print(
            "FUTURES CONFIRMED: "
            f"{sum((row.get('futures_confirmation') or {}).get('status') == 'OK' for row in rows)}"
        )
        print(f"TRADE-READY: {sum(row.get('trade_ready_time') is not None for row in rows)}")
        print("Historical futures confirmation source: M5 candles (trade history unavailable for completed days).")
        print("Futures confirmation is evaluated only at and after each SPOT READY checkpoint.")
        print("=" * 140)
