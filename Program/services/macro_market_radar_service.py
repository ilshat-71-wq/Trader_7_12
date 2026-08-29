"""Direct macro-market radar fallback for OIL, GOLD, GAS and USDRUB.

The normal project path is SPOT-first. BCS currently exposes the USD/RUB
underlying (USD000SMALL / CETS_FX) in futures metadata, while the candle
endpoint may not expose that SPOT security. This service therefore provides a
conservative, explicit fallback: macro markets are analysed directly on a
live, dated futures contract when a usable SPOT source is unavailable.

This is not a hidden futures confirmation layer. The result is labelled
FUTURES_DIRECT and the analysed contract is the instrument itself. No
portfolio sizing or order execution is performed here.
"""

from datetime import date

from services.futures_universe_service import FuturesUniverseService
from services.market_trading_universe_service import MarketTradingUniverseService
from services.futures_contract_selector_service import FuturesContractSelectorService
from services.futures_morning_radar_service import FuturesMorningRadarService


class MacroMarketRadarService:
    """Scan the four configured macro groups without requiring SPOT metadata."""

    VERSION = "1.0"
    GROUPS = MarketTradingUniverseService.MACRO_GROUPS
    MAX_DAYS_TO_EXPIRY = 3

    def __init__(self, api=None, radar_service=None, session_service=None,
                 session_money_service=None, setup_service=None):
        self.api = api
        self.futures_universe_service = FuturesUniverseService(api=self.api)
        self.radar_service = radar_service
        self.session_service = session_service
        self.session_money_service = session_money_service
        self.setup_service = setup_service
        self.selector = FuturesContractSelectorService(api=self.api)

    @staticmethod
    def _float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _days_to_expiry(cls, item):
        try:
            expiry = date.fromisoformat(str(item.get("expiry"))[:10])
        except (TypeError, ValueError):
            return None
        return (expiry - date.today()).days

    @classmethod
    def build_universe(cls, futures):
        """Keep at most two nearest valid dated contracts per macro group."""
        grouped = {group: [] for group in cls.GROUPS}
        for item in futures or []:
            if not isinstance(item, dict):
                continue
            group = MarketTradingUniverseService.futures_group(item.get("ticker"))
            if group not in grouped:
                continue
            days = cls._days_to_expiry(item)
            if days is None or days <= cls.MAX_DAYS_TO_EXPIRY:
                continue
            ticker = str(item.get("ticker") or "").upper()
            class_code = str(item.get("classCode") or "").strip()
            row = dict(item)
            row["days_to_expiry"] = days
            row["spot_ticker"] = ticker
            row["spot_class_code"] = class_code
            row["spot_group"] = group
            row["market_universe"] = group
            row["analysis_source"] = "FUTURES_DIRECT"
            row["futures_ticker"] = ticker
            row["futures_class_code"] = class_code
            row["futures_expiry"] = item.get("expiry")
            grouped[group].append(row)

        result = []
        for group, rows in grouped.items():
            rows.sort(key=lambda x: (x["days_to_expiry"], x["ticker"]))
            result.extend(rows[:2])
        return result

    def _select_contracts(self, mappings):
        """Prefer the existing liquidity/spread selector; fall back to expiry."""
        if not mappings:
            return []
        try:
            selected = self.selector.select(mappings)
        except Exception:
            selected = []
        if selected:
            return selected

        result = []
        seen = set()
        for item in mappings:
            group = item.get("spot_group")
            if group in seen:
                continue
            seen.add(group)
            result.append(dict(item))
        return result

    def scan(self, limit=None):
        if self.session_service is None or self.session_money_service is None:
            return []

        futures = self.futures_universe_service.load()
        mappings = self.build_universe(futures)
        selected = self._select_contracts(mappings)
        if not selected:
            return []

        base_radar = getattr(self.radar_service, "radar_service", None)
        if base_radar is None:
            return []

        session = self.session_service.get_session()
        trading_date = self.session_service.get_trading_day()
        results = []

        for item in selected:
            ticker = str(item.get("futures_ticker") or item.get("ticker") or "").strip().upper()
            class_code = str(item.get("futures_class_code") or item.get("classCode") or "").strip()
            group = item.get("spot_group")
            if not ticker or not class_code or group not in self.GROUPS:
                continue

            try:
                raw = base_radar.calculate(ticker=ticker, class_code=class_code)
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue

            daily = raw.get("daily") if isinstance(raw.get("daily"), dict) else {}
            trend = daily.get("trend") if isinstance(daily.get("trend"), dict) else {}
            direction = str(trend.get("direction") or "NONE").upper()
            if direction not in {"LONG", "SHORT"}:
                continue

            try:
                session_money = self.session_money_service.calculate(
                    ticker,
                    class_code,
                    trading_date=trading_date,
                    timeframe_minutes=5,
                    session=session,
                )
            except Exception:
                session_money = {}

            current_money = self._float(session_money.get("money_volume"))
            average_money = self._float(raw.get("money", {}).get("average_daily_money_volume"))
            elapsed = int(self._float(session_money.get("elapsed_minutes")))
            expected = int(self._float(session_money.get("expected_minutes")))
            money_per_minute = self._float(session_money.get("money_per_minute"))
            activity_ratio = FuturesMorningRadarService._activity_ratio(
                current_money, average_money, elapsed, expected
            )
            change = self._float(trend.get("change_percent"))
            directional_change = change if direction == "LONG" else -change

            setup = {
                "setup": "NONE",
                "setup_direction": direction,
                "setup_state": "WAIT",
                "setup_phase": "FUTURES_DIRECT",
                "setup_quality_score": 0.0,
                "entry_trigger": 0.0,
                "previous_high": 0.0,
                "previous_low": 0.0,
            }
            if self.setup_service is not None:
                try:
                    candidate_setup = self.setup_service.analyze(
                        ticker,
                        class_code,
                        direction=direction,
                        session=session,
                        trading_date=trading_date,
                    )
                    if isinstance(candidate_setup, dict):
                        setup.update(candidate_setup)
                except Exception:
                    pass

            candidate_score = min(
                100.0,
                max(
                    0.0,
                    min(activity_ratio / 3.0, 1.0) * 60.0
                    + min(max(money_per_minute, 0.0) / 50_000_000.0 * 5.0, 5.0)
                    + min(max(current_money, 0.0) / 1_000_000_000.0 * 5.0, 5.0)
                    + min(max(directional_change, 0.0) * 5.0, 15.0)
                    + min(max(self._float(setup.get("setup_quality_score")), 0.0) * 0.15, 15.0),
                ),
            )

            last_close = self._float(daily.get("last_close"))
            expiry = item.get("futures_expiry", item.get("expiry"))
            result = {
                "version": self.VERSION,
                "status": "WATCHLIST",
                "analysis_source": "FUTURES_DIRECT",
                "spot_data_status": "UNAVAILABLE_PROXY_TO_FUTURES",
                "direction": direction,
                "spot_group": group,
                "market_group": group,
                "spot_universe": group,
                "spot_ticker": ticker,
                "spot_class_code": class_code,
                "spot_name": str(item.get("name") or item.get("displayName") or group),
                "spot_type": "MACRO_FUTURES_PROXY",
                "spot_price": last_close,
                "spot_money_volume": current_money,
                "spot_average_daily_money": average_money,
                "spot_money_ratio": current_money / average_money if average_money > 0 else 0.0,
                "spot_session_activity_ratio": activity_ratio,
                "spot_money_per_minute": money_per_minute,
                "session_elapsed_minutes": elapsed,
                "session_expected_minutes": expected,
                "spot_change_percent": change,
                "change_percent": change,
                "trend_state": trend.get("state", "UNKNOWN"),
                "trend_days": int(self._float(trend.get("days"))),
                "radar_score": candidate_score,
                "candidate_score": round(candidate_score, 2),
                "relative_strength": 0.0,
                "relative_strength_score": 0.0,
                "relative_strength_signal": "UNAVAILABLE",
                "relative_strength_status": "UNAVAILABLE",
                "relative_strength_benchmark": "NOT_APPLICABLE_FOR_MACRO_DIRECT",
                "setup": setup.get("setup", "NONE"),
                "setup_direction": setup.get("setup_direction", direction),
                "setup_state": setup.get("setup_state", "WAIT"),
                "setup_phase": setup.get("setup_phase", "FUTURES_DIRECT"),
                "setup_quality_score": self._float(setup.get("setup_quality_score")),
                "impulse_percent": self._float(setup.get("impulse_percent")),
                "retracement_percent": self._float(setup.get("retracement_percent")),
                "retracement_ratio": self._float(setup.get("retracement_ratio")),
                "consolidation_candles": int(self._float(setup.get("consolidation_candles"))),
                "entry_trigger": self._float(setup.get("entry_trigger")),
                "previous_high": self._float(setup.get("previous_high")),
                "previous_low": self._float(setup.get("previous_low")),
                "impulse_high": self._float(setup.get("impulse_high")),
                "impulse_low": self._float(setup.get("impulse_low")),
                "futures_ticker": ticker,
                "futures_class_code": class_code,
                "futures_expiry": expiry,
                "days_to_expiry": item.get("days_to_expiry"),
                "selection_score": item.get("selection_score"),
                "liquidity_score": item.get("liquidity_score"),
                "spread_score": item.get("spread_score"),
                "expiry_score": item.get("expiry_score"),
                "spread_percent": item.get("spread_percent"),
                "turnover_30m": item.get("turnover_30m"),
                "trade_count_30m": item.get("trade_count_30m"),
                "depth_notional": item.get("depth_notional"),
                "bid": item.get("bid"),
                "ask": item.get("ask"),
                "last": item.get("last"),
                "futures_selection_version": item.get("futures_selection_version"),
                "futures_selection_reason": "MACRO_DIRECT_ANALYSIS",
                "futures_selection_candidates": item.get("futures_selection_candidates"),
                "mapping_method": "FUTURES_DIRECT",
                "market_session": session,
            }
            results.append(result)

        results.sort(
            key=lambda x: (
                self._float(x.get("candidate_score")),
                self._float(x.get("spot_session_activity_ratio")),
                self._float(x.get("spot_money_per_minute")),
                abs(self._float(x.get("spot_change_percent"))),
                str(x.get("spot_ticker") or ""),
            ),
            reverse=True,
        )
        if limit is not None:
            return results[: max(0, int(limit))]
        return results
