"""Two-phase SPOT-first radar with deferred futures mapping.

The live scanner must obtain the tradable SPOT universe directly from BCS.
Futures discovery is deliberately deferred until a SPOT candidate has passed
analysis/readiness.  This prevents a temporary futures-mapping problem from
silently turning the equity SPOT universe into an empty result set.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_contract_selector_service import FuturesContractSelectorService
from services.market_trading_universe_service import MarketTradingUniverseService
from services.moex_index_universe_service import MoexIndexUniverseService
from services.spot_universe_service import SpotUniverseService


class TwoPhaseFuturesMorningRadarService(FuturesMorningRadarService):
    """FAST SPOT screen -> DEEP SPOT analysis -> readiness -> futures mapping."""

    VERSION = "1.6"
    PRELIMINARY_WORKERS = 2
    DEEP_SPOT_LIMIT = 5
    DEEP_DIRECTION_LIMIT = 4
    MAX_CONTRACTS_PER_SPOT = 2
    MAX_DAYS_TO_EXPIRY = 3

    def __init__(
        self,
        *args,
        index_universe_service=None,
        trading_universe_service=None,
        futures_contract_selector=None,
        spot_universe_service=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.index_universe_service = index_universe_service or MoexIndexUniverseService()
        self.trading_universe_service = trading_universe_service or MarketTradingUniverseService()
        self.spot_universe_service = spot_universe_service or SpotUniverseService(api=self.api)
        self.futures_contract_selector = futures_contract_selector or FuturesContractSelectorService(
            api=getattr(self.mapping_service, "api", None)
        )

    @staticmethod
    def _parse_expiry(value):
        if value is None:
            return None
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

    @classmethod
    def _select_current_contracts(cls, mappings):
        """Keep only non-expiring futures references for post-SPOT mapping."""
        grouped = {}
        today = date.today()
        for mapping in mappings or []:
            if not isinstance(mapping, dict):
                continue
            spot_ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            expiry = cls._parse_expiry(mapping.get("futures_expiry"))
            if not spot_ticker or expiry is None:
                continue
            days_to_expiry = (expiry - today).days
            if days_to_expiry <= cls.MAX_DAYS_TO_EXPIRY:
                continue
            item = dict(mapping)
            item["futures_expiry"] = expiry.isoformat()
            item["days_to_expiry"] = days_to_expiry
            grouped.setdefault(spot_ticker, []).append(item)

        selected = []
        for candidates in grouped.values():
            candidates.sort(
                key=lambda item: (
                    cls._parse_expiry(item.get("futures_expiry")) or date.max,
                    str(item.get("futures_ticker") or ""),
                )
            )
            selected.extend(candidates[: cls.MAX_CONTRACTS_PER_SPOT])
        return selected

    def _select_futures_mapping(self, mappings):
        eligible = self._select_current_contracts(mappings)
        if not eligible:
            return None
        try:
            selected = self.futures_contract_selector.select(eligible)
        except Exception as exc:
            print(f"⚠️ Futures mapping selector failed: {type(exc).__name__}")
            return None
        return selected[0] if isinstance(selected, list) and selected else None

    def _load_direct_spot_universe(self):
        """Load canonical IMOEX TQBR equities directly from SPOT metadata."""
        try:
            spots = self.spot_universe_service.load()
        except Exception as exc:
            print(f"⚠️ SPOT universe load failed: {type(exc).__name__}")
            return []

        imoex = self.index_universe_service.load()
        if not imoex:
            return []

        result = []
        seen = set()
        for item in spots:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("spot_ticker") or "").strip().upper()
            class_code = str(item.get("spot_class_code") or "").strip().upper()
            instrument_type = str(item.get("spot_instrument_type") or "").strip().upper()
            if not ticker or not class_code or ticker not in imoex:
                continue
            # BCS may return the same stock separately for SMAL/SPBRU/TQBR.
            # IMOEX equity screening must use the canonical MOEX TQBR board.
            if instrument_type != "STOCK" or class_code != "TQBR":
                continue
            if ticker in seen:
                continue
            seen.add(ticker)
            result.append(
                {
                    "spot_ticker": ticker,
                    "spot_class_code": "TQBR",
                    "spot_group": "MOEX_STOCK",
                    "spot_universe": "IMOEX",
                    "market_universe": "IMOEX",
                    "spot_type": "SPOT",
                    "spot_name": ticker,
                    "mapping_method": "DIRECT_SPOT_UNIVERSE",
                    "futures_ticker": "",
                    "futures_class_code": "",
                    "futures_expiry": None,
                }
            )
        result.sort(key=lambda item: item["spot_ticker"])
        print(f"IMOEX CANONICAL SPOT: {len(result)} TQBR constituents loaded")
        return result

    def _prepare_universe(self, mappings):
        """Normalize an explicitly supplied universe without requiring futures."""
        if not isinstance(mappings, list):
            return []
        result = []
        seen = set()
        for item in mappings:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("spot_ticker") or "").strip().upper()
            class_code = str(item.get("spot_class_code") or "").strip()
            if not ticker or not class_code:
                continue
            group = self.trading_universe_service.spot_group(item)
            if group != "MOEX_STOCK":
                continue
            key = (ticker, class_code)
            if key in seen:
                continue
            seen.add(key)
            normalized = dict(item)
            normalized["spot_group"] = "MOEX_STOCK"
            normalized["spot_universe"] = "IMOEX"
            normalized.setdefault("market_universe", "IMOEX")
            result.append(normalized)
        return result

    def _preliminary_one(self, spot_key):
        """FAST screen using SPOT candles and current-session SPOT money."""
        ticker, class_code = spot_key
        try:
            base = getattr(self.radar_service, "radar_service", None)
            if base is None:
                return spot_key, None
            raw = base.calculate(ticker=ticker, class_code=class_code)
            if not isinstance(raw, dict):
                return spot_key, None

            daily = raw.get("daily") if isinstance(raw.get("daily"), dict) else {}
            trend = daily.get("trend") if isinstance(daily.get("trend"), dict) else {}
            money = raw.get("money") if isinstance(raw.get("money"), dict) else {}
            direction = str(trend.get("direction", "NONE")).upper()
            change_percent = float(trend.get("change_percent", 0) or 0)
            average_daily_money = float(money.get("average_daily_money_volume", 0) or 0)

            session = self.session_service.get_session()
            trading_date = self.session_service.get_trading_day()
            session_money = self.session_money_service.calculate(
                ticker,
                class_code,
                trading_date=trading_date,
                timeframe_minutes=5,
                session=session,
            ) or {}
            current_money = float(session_money.get("money_volume", 0) or 0)
            elapsed = int(session_money.get("elapsed_minutes", 0) or 0)
            expected = int(session_money.get("expected_minutes", 0) or 0)
            money_per_minute = float(session_money.get("money_per_minute", 0) or 0)
            activity_ratio = self._activity_ratio(
                current_money, average_daily_money, elapsed, expected
            )
            directional_change = (
                change_percent if direction == "LONG"
                else -change_percent if direction == "SHORT"
                else 0.0
            )
            return spot_key, {
                "status": "OK",
                "direction": direction,
                "spot_money_volume": current_money,
                "spot_money_per_minute": money_per_minute,
                "spot_session_activity_ratio": activity_ratio,
                "average_daily_money": average_daily_money,
                "change_percent": change_percent,
                "directional_change": directional_change,
                "elapsed_minutes": elapsed,
                "expected_minutes": expected,
                "radar_score": round(
                    max(0.0, activity_ratio) * 100.0
                    + max(0.0, money_per_minute) / 1_000_000.0
                    + max(0.0, directional_change),
                    2,
                ),
            }
        except Exception as exc:
            return spot_key, {"status": "ERROR", "error": str(exc)}

    def _preliminary_scan(self, mappings):
        keys = sorted(
            {
                (
                    str(item.get("spot_ticker") or "").strip().upper(),
                    str(item.get("spot_class_code") or "").strip(),
                )
                for item in mappings
                if str(item.get("spot_ticker") or "").strip()
                and str(item.get("spot_class_code") or "").strip()
            }
        )
        if not keys:
            return {}
        results = {}
        with ThreadPoolExecutor(
            max_workers=min(self.PRELIMINARY_WORKERS, len(keys)),
            thread_name_prefix="radar-pre",
        ) as executor:
            futures = [executor.submit(self._preliminary_one, key) for key in keys]
            for future in as_completed(futures):
                key, result = future.result()
                if result is not None:
                    results[key] = result
        return results

    @classmethod
    def _select_deep_keys(cls, preliminary):
        valid = [
            (key, value)
            for key, value in preliminary.items()
            if isinstance(value, dict) and str(value.get("status", "")).upper() == "OK"
        ]

        def f(value):
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        ranked = sorted(
            valid,
            key=lambda item: (
                f(item[1].get("spot_session_activity_ratio")),
                f(item[1].get("spot_money_per_minute")),
                f(item[1].get("spot_money_volume")),
                f(item[1].get("directional_change")),
            ),
            reverse=True,
        )
        selected = []
        for key, value in ranked:
            if len(selected) >= cls.DEEP_SPOT_LIMIT:
                break
            if (
                f(value.get("spot_session_activity_ratio")) <= 0
                and f(value.get("spot_money_per_minute")) <= 0
                and f(value.get("spot_money_volume")) <= 0
            ):
                continue
            selected.append(key)
        return set(selected)

    def _attach_futures_after_spot(self, results):
        """Load futures mapping only after SPOT analysis has produced results."""
        ready = [
            item for item in results
            if str(item.get("signal_state") or "WAIT").upper() in {"READY", "CONFIRMED"}
            and str(item.get("setup_state") or "WAIT").upper() in {"READY", "CONFIRMED"}
        ]
        if not ready:
            return results

        try:
            mappings = self.mapping_service.load()
        except Exception as exc:
            print(f"⚠️ Deferred futures mapping unavailable: {type(exc).__name__}")
            return results

        by_spot = {}
        for mapping in mappings or []:
            if not isinstance(mapping, dict):
                continue
            ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            if ticker:
                by_spot.setdefault(ticker, []).append(mapping)

        for item in ready:
            ticker = str(item.get("spot_ticker") or "").strip().upper()
            selected = self._select_futures_mapping(by_spot.get(ticker, []))
            if not selected:
                continue
            for field in (
                "futures_ticker", "futures_class_code", "futures_expiry", "days_to_expiry",
                "selection_score", "liquidity_score", "spread_score", "expiry_score",
                "spread_percent", "turnover_30m", "trade_count_30m", "depth_notional",
                "bid", "ask", "last", "futures_selection_version", "futures_selection_candidates",
            ):
                if field in selected:
                    item[field] = selected.get(field)
            item["futures_selection_reason"] = selected.get(
                "futures_selection_reason", "POST_SPOT_READINESS_MAPPING"
            )
            item["mapping_method"] = selected.get("mapping_method", "POST_SPOT_READINESS_MAPPING")
        return results

    def scan(self, mappings=None, limit=None):
        """Run SPOT analysis first; use futures only as a post-readiness reference."""
        if mappings is None:
            mappings = self._load_direct_spot_universe()
        else:
            mappings = self._prepare_universe(mappings)
        if not mappings:
            return []

        preliminary = self._preliminary_scan(mappings)
        deep_keys = self._select_deep_keys(preliminary)
        deep_mappings = [
            item
            for item in mappings
            if (
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("spot_class_code") or "").strip(),
            ) in deep_keys
        ]
        if not deep_mappings:
            return []

        results = super().scan(mappings=deep_mappings, limit=limit)
        self._attach_futures_after_spot(results)

        for item in results:
            item["scan_phase"] = "DEEP"
            item["spot_universe"] = "IMOEX"
            item["market_group"] = "MOEX_STOCK"
            key = (
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("spot_class_code") or "").strip(),
            )
            item["preliminary_radar_score"] = round(
                float(preliminary.get(key, {}).get("radar_score", item.get("radar_score", 0)) or 0),
                2,
            )
        return results

    @staticmethod
    def print_results(results):
        print()
        print("=" * 128)
        print("TRADER_7_12 PRO - SPOT DIRECTION -> SETUP -> TRIGGER -> READINESS -> FUTURES MAPPING")
        print("=" * 128)
        print()
        print(f"{'RANK':<6}{'SPOT':<12}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<18}{'TRIGGER':>12}")
        print("-" * 128)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('spot_ticker', '-'): <12}"
                f"{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}"
                f"{str(item.get('setup', '-')):<18}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
            )
        if results:
            first = results[0]
            diagnostics = first.get("scan_diagnostics")
            print()
            print(f"SESSION: {first.get('market_session_label', first.get('market_session', '-'))}")
            print(f"TIME: {first.get('market_date', '-')} {first.get('market_time', '-')} MSK")
            if diagnostics:
                print(
                    "DIAGNOSTICS: "
                    f"RADAR={diagnostics.get('radar_results', 0)} "
                    f"CANDIDATES={diagnostics.get('candidates', 0)} "
                    f"SELECTED={diagnostics.get('selected', 0)} "
                    f"READY={diagnostics.get('ready', 0)} "
                    f"CONFIRMED={diagnostics.get('confirmed', 0)} "
                    f"WATCH={diagnostics.get('watch', 0)} "
                    f"WAIT={diagnostics.get('wait', 0)}"
                )
        else:
            print("NO WATCHLIST CANDIDATES")
        print()
        print("SPOT is the source of direction, money/activity, RS, setup, trigger and readiness.")
        print("Futures are mapped only after a SPOT candidate reaches readiness.")
        print("Scanner is read-only; no orders, sizing or SL/TP.")
        print("=" * 128)
