"""Two-phase futures radar: broad market screen, deep analysis for finalists."""

from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.moex_index_universe_service import MoexIndexUniverseService
from services.market_trading_universe_service import MarketTradingUniverseService


class TwoPhaseFuturesMorningRadarService(FuturesMorningRadarService):
    """Scan IMOEX equities plus the configured macro markets."""

    VERSION = "1.2"
    PRELIMINARY_WORKERS = 2
    DEEP_SPOT_LIMIT = 8
    DEEP_DIRECTION_LIMIT = 4
    MAX_CONTRACTS_PER_SPOT = 2
    MAX_DAYS_TO_EXPIRY = 3

    def __init__(self, *args, index_universe_service=None, trading_universe_service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.index_universe_service = index_universe_service or MoexIndexUniverseService()
        self.trading_universe_service = trading_universe_service or MarketTradingUniverseService()

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
        """Keep the nearest two eligible contracts for every underlying.

        The final choice between these two is made later by the candidate
        service using actual futures liquidity/turnover. Contracts with three
        or fewer calendar days to expiry are excluded unconditionally.
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

    def _prepare_universe(self, mappings):
        """Keep current IMOEX equities and OIL/GOLD/GAS/USDRUB mappings."""
        if not isinstance(mappings, list):
            return []

        # First apply the dynamic IMOEX gate to equities only. Macro mappings
        # are intentionally preserved and then classified by the unified
        # trading-universe service.
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
        """
        FAST SCREEN.

        The preliminary stage answers only:
        "Where is money/activity appearing TODAY?"

        Historical average turnover is used only as the denominator for
        activity_ratio. It is NOT used as the primary ranking criterion.
        Expensive RS/setup/futures confirmation remain in the DEEP stage.
        """
        ticker, class_code = spot_key

        try:
            base = getattr(self.radar_service, "radar_service", None)
            if base is None:
                return spot_key, None

            raw = base.calculate(
                ticker=ticker,
                class_code=class_code,
            )

            if not isinstance(raw, dict):
                return spot_key, None

            daily = raw.get("daily")
            if not isinstance(daily, dict):
                daily = {}

            trend = daily.get("trend")
            if not isinstance(trend, dict):
                trend = {}

            money = raw.get("money")
            if not isinstance(money, dict):
                money = {}

            direction = str(
                trend.get("direction", "NONE")
            ).upper()

            change_percent = float(
                trend.get("change_percent", 0) or 0
            )

            average_daily_money = float(
                money.get("average_daily_money_volume", 0) or 0
            )

            # Use the same current-session money source as the real
            # FuturesMorningRadarService. This keeps FAST and DEEP
            # based on exactly the same money/activity definition.
            session_money_service = self.session_money_service
            session_service = self.session_service

            if session_money_service is None or session_service is None:
                return spot_key, {
                    "status": "ERROR",
                    "error": "Session money service unavailable",
                }

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

            current_money = float(
                session_money.get("money_volume", 0) or 0
            )
            elapsed_minutes = int(
                session_money.get("elapsed_minutes", 0) or 0
            )
            expected_minutes = int(
                session_money.get("expected_minutes", 0) or 0
            )
            money_per_minute = float(
                session_money.get("money_per_minute", 0) or 0
            )

            activity_ratio = FuturesMorningRadarService._activity_ratio(
                current_money,
                average_daily_money,
                elapsed_minutes,
                expected_minutes,
            )

            # Directional movement is secondary to current money/activity.
            directional_change = (
                change_percent
                if direction == "LONG"
                else -change_percent
                if direction == "SHORT"
                else 0.0
            )

            return spot_key, {
                "status": "OK",
                "direction": direction,

                # TODAY'S MONEY — primary FAST SCREEN factors
                "spot_money_volume": current_money,
                "spot_money_per_minute": money_per_minute,
                "spot_session_activity_ratio": activity_ratio,

                # Historical turnover is retained only for context /
                # denominator, never as the main ranking factor.
                "average_daily_money": average_daily_money,

                # Secondary directional context.
                "change_percent": change_percent,
                "directional_change": directional_change,

                "elapsed_minutes": elapsed_minutes,
                "expected_minutes": expected_minutes,
            }

        except Exception as exc:
            return spot_key, {
                "status": "ERROR",
                "error": str(exc),
            }

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
        """
        Select finalists primarily by TODAY'S money/activity.

        Priority:
        1. unusual current-session activity;
        2. money flow per minute;
        3. absolute current-session money;
        4. directional movement.

        Historical average turnover is intentionally NOT a ranking factor.
        It is already embedded in activity_ratio as the asset's own baseline.
        """
        valid = [
            (key, value)
            for key, value in preliminary.items()
            if (
                isinstance(value, dict)
                and str(value.get("status", "")).upper() == "OK"
            )
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

        # Keep directional diversity where possible, but do NOT sacrifice
        # a materially stronger money/activity leader just to fill LONG/SHORT.
        selected = []
        selected_keys = set()

        for key, value in ranked:
            if len(selected) >= cls.DEEP_SPOT_LIMIT:
                break

            activity = f(value.get("spot_session_activity_ratio"))
            money_per_minute = f(value.get("spot_money_per_minute"))
            money_volume = f(value.get("spot_money_volume"))

            # Ignore instruments with no meaningful current-session flow.
            if activity <= 0 and money_per_minute <= 0 and money_volume <= 0:
                continue

            selected.append(key)
            selected_keys.add(key)

        return set(selected)

    def scan(self, mappings=None, limit=None):
        """Fast unified-market pass, then deep SPOT analysis for finalists."""
        if mappings is None:
            mappings = self._load_mappings_cached()
        if not isinstance(mappings, list):
            return []

        mappings = self._select_current_contracts(mappings)
        mappings = self._prepare_universe(mappings)
        if not mappings:
            return []

        preliminary = self._preliminary_scan(mappings)
        deep_keys = self._select_deep_keys(preliminary)

        # Network failures in the FAST stage must not turn a read-only market
        # scan into a false "NO FINAL CANDIDATES".  If FAST produced no usable
        # finalists, fall back to the proven base radar over the prepared
        # universe.  The base radar applies its normal liquidity, direction,
        # RS, group and candidate filters; this changes resilience only, not
        # trading criteria.
        if not deep_keys:
            return super().scan(mappings=mappings, limit=limit)

        deep_mappings = [
            item for item in mappings
            if (str(item.get("spot_ticker") or "").strip().upper(), str(item.get("spot_class_code") or "").strip()) in deep_keys
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
