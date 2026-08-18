"""Two-phase futures radar: cheap SPOT screen first, deep analysis only for finalists."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from services.futures_morning_radar_service import FuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService


class TwoPhaseFuturesMorningRadarService(FuturesMorningRadarService):
    """Keep the existing radar contract while reducing expensive history calls."""

    VERSION = "0.9"
    # BCS rate-limits concurrent history requests. Keep the preliminary pass
    # parallel, but bounded enough to avoid turning the fast phase into a burst
    # of HTTP 429/timeout responses during an active session.
    PRELIMINARY_WORKERS = 2
    DEEP_SPOT_LIMIT = 5
    DEEP_DIRECTION_LIMIT = 3

    def _is_target_spot(self, mapping):
        """Limit the expensive SPOT screen to the project's five target groups."""
        if not isinstance(mapping, dict):
            return False
        try:
            return FuturesTradeCandidateService._spot_group(mapping) in FuturesTradeCandidateService.TARGET_SPOT_GROUPS
        except Exception:
            return False

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
        # Do not spend D-candle requests on unrelated futures (indices,
        # technical/other derivatives, etc.). The final scanner is explicitly
        # limited to stocks, gas, oil, USD and gold.
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
        """Select deep finalists across the full market while preserving LONG/SHORT competition."""
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

        # Keep both directions alive in the deep phase. This is only a
        # performance shortlist; the final ranking and filters remain unchanged.
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

        # Fill remaining deep slots by the global preliminary score.
        for key, _value in ranked:
            if len(selected) >= cls.DEEP_SPOT_LIMIT:
                break
            if key not in selected_keys:
                selected.append(key)
                selected_keys.add(key)

        return set(selected)

    def scan(self, mappings=None, limit=None):
        """Fast pass over target SPOTs, then deep H1/RS/M5 analysis for finalists."""
        if mappings is None:
            mappings = self._load_mappings_cached()
        if not isinstance(mappings, list):
            return []
        mappings = self._select_current_contracts(mappings)
        if not mappings:
            return []

        preliminary = self._preliminary_scan(mappings)
        deep_keys = self._select_deep_keys(preliminary)

        # If a test double does not expose the underlying MorningRadarService,
        # preserve the original behavior instead of silently returning nothing.
        if not deep_keys and not hasattr(self.radar_service, "radar_service"):
            return super().scan(mappings=mappings, limit=limit)

        deep_mappings = [
            item for item in mappings
            if (str(item.get("spot_ticker") or "").strip().upper(), str(item.get("spot_class_code") or "").strip()) in deep_keys
        ]

        results = super().scan(mappings=deep_mappings, limit=limit)
        for item in results:
            item["scan_phase"] = "DEEP"
            key = (
                str(item.get("spot_ticker") or "").strip().upper(),
                str(item.get("spot_class_code") or "").strip(),
            )
            item["preliminary_radar_score"] = round(float(preliminary.get(key, {}).get("radar_score", item.get("radar_score", 0)) or 0), 2)
        return results
