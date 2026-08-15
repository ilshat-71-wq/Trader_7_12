"""
Trader_7_12 Pro

Historical Universe Morning Replay Service.

Purpose:
- build the dynamic Futures -> SPOT universe for a historical date;
- choose the two nearest valid futures contracts per SPOT at that date;
- calculate historical daily direction from completed D candles;
- filter by historical average daily money turnover;
- replay the existing SPOT M5 setup detector at morning checkpoints;
- report the first WAIT/READY transition without using future candles.

Read-only. No orders are sent.
"""

from datetime import date, datetime, timedelta, timezone

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.history_candle_service import HistoryCandleService
from services.morning_radar_service import MorningRadarService
from services.morning_replay_service import MorningReplayService


class HistoricalUniverseReplayService:
    VERSION = "0.2"
    DEFAULT_MIN_MONEY = 100_000_000.0
    DEFAULT_AVERAGE_DAYS = 5
    MAX_CONTRACTS_PER_SPOT = 2

    def __init__(self, mapping_service=None, history_service=None, replay_service=None):
        self.mapping_service = mapping_service or FuturesSpotMappingService()
        self.history_service = history_service or HistoryCandleService()
        self.replay_service = replay_service or MorningReplayService(
            history_service=self.history_service
        )
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

    def load_mappings_for_date(self, trading_date):
        """Load dynamic mappings and keep the two nearest valid contracts per SPOT."""
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
            if not spot or expiry is None or expiry < trading_date:
                continue

            candidate = dict(mapping)
            candidate["futures_expiry"] = expiry.isoformat()
            grouped.setdefault(spot, []).append(candidate)

        selected = []
        for candidates in grouped.values():
            candidates.sort(
                key=lambda item: (
                    self._parse_expiry(item.get("futures_expiry")) or date.max,
                    str(item.get("futures_ticker") or ""),
                )
            )
            selected.extend(candidates[:self.MAX_CONTRACTS_PER_SPOT])

        return sorted(
            selected,
            key=lambda item: (
                str(item.get("spot_ticker") or ""),
                self._parse_expiry(item.get("futures_expiry")) or date.max,
                str(item.get("futures_ticker") or ""),
            )
        )

    def load_daily_candles(self, ticker, class_code, trading_date):
        """Load completed daily candles strictly before the replay date."""
        trading_date = self._as_date(trading_date)
        end_moscow = datetime.combine(
            trading_date,
            datetime.min.time(),
        ).replace(tzinfo=self.history_service.MOSCOW_TZ)
        start_utc = end_moscow.astimezone(timezone.utc) - timedelta(days=12)
        end_utc = end_moscow.astimezone(timezone.utc)

        try:
            data = self.history_service.trade_service.api.get_candles(
                ticker,
                class_code,
                interval="D",
                start_time=start_utc,
                end_time=end_utc,
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
                "time": bar.get("time"),
                "date": candle_date.isoformat(),
                "open": float(bar.get("open") or 0),
                "high": float(bar.get("high") or 0),
                "low": float(bar.get("low") or 0),
                "close": close,
                "volume": volume,
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

    def replay(self, trading_date, min_money=None, checkpoints=None, limit=None):
        trading_date = self._as_date(trading_date)
        min_money = self.DEFAULT_MIN_MONEY if min_money is None else float(min_money)
        mappings = self.load_mappings_for_date(trading_date)
        rows = []

        for mapping in mappings:
            spot = str(mapping.get("spot_ticker") or "").strip().upper()
            spot_class = str(mapping.get("spot_class_code") or "").strip()
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

            ready = next((item for item in replay if item["setup_state"] == "READY"), None)
            setup_seen = next((item for item in replay if item["setup"] != "NONE"), None)

            rows.append({
                "futures_ticker": mapping.get("futures_ticker"),
                "futures_class_code": mapping.get("futures_class_code"),
                "futures_expiry": mapping.get("futures_expiry"),
                "spot_ticker": spot,
                "spot_class_code": spot_class,
                "direction": direction,
                "trend_state": trend.get("state"),
                "trend_change_percent": trend.get("change_percent", 0.0),
                "average_daily_money": avg_money,
                "setup_first_seen": setup_seen.get("checkpoint") if setup_seen else None,
                "ready_time": ready.get("checkpoint") if ready else None,
                "entry_trigger": ready.get("entry_trigger", 0.0) if ready else 0.0,
                "replay": replay,
            })

        rows.sort(
            key=lambda item: (
                item["ready_time"] is not None,
                item["average_daily_money"],
            ),
            reverse=True,
        )
        if limit is not None:
            rows = rows[:int(limit)]
        return rows

    @staticmethod
    def print_results(rows, trading_date, min_money):
        print()
        print("=" * 130)
        print("TRADER_7_12 PRO - DYNAMIC HISTORICAL MORNING REPLAY")
        print("READ ONLY — NO ORDERS")
        print(f"DATE: {trading_date}  |  MIN AVG DAILY MONEY: {min_money:,.0f}")
        print("=" * 130)
        print(f"{'FUTURES':<12}{'SPOT':<9}{'DIR':<7}{'AVG MONEY':>16}{'SETUP':>10}{'READY':>9}{'TRIGGER':>14}")
        print("-" * 130)
        for row in rows:
            print(
                f"{str(row['futures_ticker'] or '-'): <12}"
                f"{row['spot_ticker']:<9}"
                f"{row['direction']:<7}"
                f"{row['average_daily_money']:>16,.0f}"
                f"{str(row['setup_first_seen'] or '-'):>10}"
                f"{str(row['ready_time'] or '-'):>9}"
                f"{float(row['entry_trigger'] or 0):>14.4f}"
            )
        print("-" * 130)
        ready_count = sum(1 for row in rows if row["ready_time"] is not None)
        print(f"MAPPED LIQUID FUTURES/SPOTS: {len(rows)}")
        print(f"READY SETUPS: {ready_count}")
        print("=" * 130)
