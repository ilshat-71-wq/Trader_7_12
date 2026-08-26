"""Two-phase futures radar: broad market screen, deep analysis for finalists."""

from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.futures_contract_selector_service import FuturesContractSelectorService
from services.moex_index_universe_service import MoexIndexUniverseService
from services.market_trading_universe_service import MarketTradingUniverseService


class TwoPhaseFuturesMorningRadarService(FuturesMorningRadarService):
    """Scan IMOEX equities plus the configured macro markets."""

    VERSION = "1.4"
    PRELIMINARY_WORKERS = 2
    DEEP_SPOT_LIMIT = 5
    DEEP_DIRECTION_LIMIT = 4
    MAX_CONTRACTS_PER_SPOT = 2
    MAX_DAYS_TO_EXPIRY = 3

    def __init__(self, *args, index_universe_service=None, trading_universe_service=None, futures_contract_selector=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_universe_service = index_universe_service or MoexIndexUniverseService()
        self.trading_universe_service = trading_universe_service or MarketTradingUniverseService()
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
        """Build the eligible futures reference set for post-readiness mapping.

        This method is deliberately NOT called before SPOT analysis. It is
        invoked only after a SPOT candidate has a valid setup and trigger.
        Contracts with three or fewer calendar days to expiry are excluded.
        """
        grouped = {}
        today = date.today()

        for mapping in mappings or []:
            if not isinstance(mapping, dict):
                continue

            spot_ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            if not spot_ticker:
                continue

            expiry = cls._parse_expiry(mapping.get("futures_expiry"))
            if expiry is None:
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

        return sorted(
            selected,
            key=lambda item: (
                str(item.get("spot_ticker") or ""),
                cls._parse_expiry(item.get("futures_expiry")) or date.max,
                str(item.get("futures_ticker") or ""),
            ),
        )

    def _select_futures_mapping(self, mappings):
        """Select the live futures contract only after SPOT readiness."""
        eligible = self._select_current_contracts(mappings)
        if not eligible:
            return None
        selected = self.futures_contract_selector.select(eligible)
        if isinstance(selected, list) and selected:
            return selected[0]
        return None

    def _prepare_universe(self, mappings):
        """Keep current IMOEX equities and OIL/GOLD/GAS/USDRUB mappings."""
        if not isinstance(mappings, list):
            return []

        imoex = self.index_universe_service.filter_mappings(mappings)

        macro = []
        for item in mappings:
            if not isinstance(item, dict):
                continue
            group = self.trading_universe_service.futures_group(item.get("futures_ticker"))
            if group in self.trading_universe_service.MACRO_GROUPS:
                macro.append(item)

        combined = imoex + macro
        result = []
        seen = set()
        for item in combined:
            key = (
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("futures_ticker") or "").strip().upper(),
                str(item.get("futures_class_code") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)

        return self.trading_universe_service.filter_mappings(result)

    def _is_target_spot(self, mapping):
        return self.trading_universe_service.spot_group(mapping) in self.trading_universe_service.TARGET_GROUPS

    def _preliminary_one(self, spot_key):
        """FAST screen: identify where current-session money/activity appears."""
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

            session_money_service = self.session_money_service
            session_service = self.session_service
            if session_money_service is None or session_service is None:
                return spot_key, {"status": "ERROR", "error": "Session money service unavailable"}

            trading_date = session_service.get_trading_day()
            session = session_service.get_session()
            session_money = session_money_service.calculate(
                ticker,
                class_code,
                trading_date=trading_date,
                timeframe_minutes=5,
                session=session,
            )
            if not isinstance(session_money, dict):
                session_money = {}

            current_money = float(session_money.get("money_volume", 0) or 0)
            elapsed_minutes = int(session_money.get("elapsed_minutes", 0) or 0)
            expected_minutes = int(session_money.get("expected_minutes", 0) or 0)
            money_per_minute = float(session_money.get("money_per_minute", 0) or 0)

            activity_ratio = FuturesMorningRadarService._activity_ratio(
                current_money,
                average_daily_money,
                elapsed_minutes,
                expected_minutes,
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
                "elapsed_minutes": elapsed_minutes,
                "expected_minutes": expected_minutes,
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
        keys = sorted({
            (str(item.get("spot_ticker") or "").strip().upper(), str(item.get("spot_class_code") or "").strip())
            for item in mappings
            if self._is_target_spot(item)
            and str(item.get("spot_ticker") or "").strip()
            and str(item.get("spot_class_code") or "").strip()
        })
        results = {}
        if not keys:
            return results
        with ThreadPoolExecutor(max_workers=min(self.PRELIMINARY_WORKERS, len(keys)), thread_name_prefix="radar-pre") as executor:
            futures = [executor.submit(self._preliminary_one, key) for key in keys]
            for future in as_completed(futures):
                key, result = future.result()
                if result is not None:
                    results[key] = result
        return results

    @classmethod
    def _select_deep_keys(cls, preliminary):
        """Select DEEP finalists primarily by today's money/activity."""
        valid = [
            (key, value) for key, value in preliminary.items()
            if isinstance(value, dict) and str(value.get("status", "")).upper() == "OK"
        ]

        def f(value, default=0.0):
            try:
                return float(value or default)
            except (TypeError, ValueError):
                return default

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
            activity = f(value.get("spot_session_activity_ratio"))
            money_per_minute = f(value.get("spot_money_per_minute"))
            money_volume = f(value.get("spot_money_volume"))
            if activity <= 0 and money_per_minute <= 0 and money_volume <= 0:
                continue
            selected.append(key)

        return set(selected)

    def scan(self, mappings=None, limit=None):
        """FAST SPOT screen -> DEEP SPOT -> SPOT readiness -> futures mapping."""
        if mappings is None:
            mappings = self._load_mappings_cached()
        if not isinstance(mappings, list):
            return []

        # IMPORTANT: do not select/expire futures before the SPOT screen.
        # The same SPOT asset may remain valid while one futures contract is
        # expiring. Futures selection is now deferred to _select_futures_mapping.
        mappings = self._prepare_universe(mappings)
        if not mappings:
            return []

        preliminary = self._preliminary_scan(mappings)
        deep_keys = self._select_deep_keys(preliminary)
        if not deep_keys:
            results = super().scan(mappings=mappings, limit=limit)
        else:
            deep_mappings = [
                item for item in mappings
                if (
                    str(item.get("spot_ticker") or "").strip().upper(),
                    str(item.get("spot_class_code") or "").strip(),
                ) in deep_keys
            ]
            results = super().scan(mappings=deep_mappings, limit=limit)

        for item in results:
            item["scan_phase"] = "DEEP"
            group = self.trading_universe_service.spot_group(item)
            item["spot_universe"] = "IMOEX" if group == "MOEX_STOCK" else group
            item["market_group"] = group
            key = (
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("spot_class_code") or "").strip(),
            )
            item["preliminary_radar_score"] = round(float(preliminary.get(key, {}).get("radar_score", item.get("radar_score", 0)) or 0), 2)
        return results
