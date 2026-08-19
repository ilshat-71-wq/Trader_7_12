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
            trend_score = self.radar_service.calculate_trend_score(trend)
            money_score = self.radar_service.calculate_money_score(money)
            radar_score = self.radar_service.calculate_radar_score(trend_score, money_score)
            return spot_key, {
                "status": "OK",
                "direction": str(trend.get("direction", "NONE")).upper(),
                "radar_score": float(radar_score or 0),
                "average_daily_money": float(money.get("average_daily_money_volume", 0) or 0),
                "trend_score": float(trend_score or 0),
                "money_score": float(money_score or 0),
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
        valid = [
            (key, value)
            for key, value in preliminary.items()
            if isinstance(value, dict) and str(value.get("status", "")).upper() == "OK"
        ]
        ranked = sorted(
            valid,
            key=lambda item: (
                item[1].get("radar_score", 0),
                item[1].get("average_daily_money", 0),
            ),
            reverse=True,
        )

        selected = []
        selected_keys = set()
        for direction in ("LONG", "SHORT"):
            count = 0
            for key, value in ranked:
                if key in selected_keys or str(value.get("direction", "")).upper() != direction:
                    continue
                selected.append(key)
                selected_keys.add(key)
                count += 1
                if count >= cls.DEEP_DIRECTION_LIMIT or len(selected) >= cls.DEEP_SPOT_LIMIT:
                    break
            if len(selected) >= cls.DEEP_SPOT_LIMIT:
                break

        for key, _value in ranked:
            if len(selected) >= cls.DEEP_SPOT_LIMIT:
                break
            if key not in selected_keys:
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

        if not deep_keys and not hasattr(self.radar_service, "radar_service"):
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
