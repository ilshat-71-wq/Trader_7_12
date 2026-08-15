"""Stage 1 read-only diagnostics for the dynamic BCS Futures -> SPOT universe.

This module is intentionally small and side-effect free. It is used to inspect
why a BCS future did or did not map to a SPOT instrument before changing the
trading pipeline itself.
"""

from collections import Counter

from services.futures_spot_mapping_service import FuturesSpotMappingService


class Stage1MappingDiagnostic:
    """Explain mapping outcomes without making trading decisions."""

    def __init__(self, mapping_service=None):
        self.mapping_service = mapping_service or FuturesSpotMappingService()

    def analyze(self, futures, spots):
        """Return mapping statistics and per-future failure reasons."""
        spot_index = self.mapping_service._build_spot_index(spots)
        mapped = []
        failures = []

        for future in futures or []:
            result, reason = self._map_with_reason(future, spots or [], spot_index)
            if result is not None:
                mapped.append(result)
            else:
                failures.append({
                    "futures_ticker": (future or {}).get("ticker"),
                    "reason": reason,
                    "metadata": self._metadata_snapshot(future or {}),
                })

        counts = Counter(item["reason"] for item in failures)
        return {
            "futures": len(futures or []),
            "spots": len(spots or []),
            "mapped": len(mapped),
            "unmapped": len(failures),
            "failure_counts": dict(counts),
            "mapped_rows": mapped,
            "failures": failures,
        }

    def _map_with_reason(self, future, spots, spot_index):
        if not isinstance(future, dict):
            return None, "INVALID_FUTURE"

        ticker = str(future.get("ticker") or "").strip().upper()
        class_code = str(future.get("classCode") or "").strip()
        if not ticker or not class_code:
            return None, "MISSING_FUTURE_ID"

        explicit = self.mapping_service._explicit_underlying(future)
        if explicit["ticker"]:
            candidates = spot_index.get(explicit["ticker"], [])
            if explicit["class_code"]:
                candidates = [
                    item for item in candidates
                    if self.mapping_service._class_code(item) == explicit["class_code"]
                ]

            if len(candidates) == 1:
                return self.mapping_service._result(
                    future, candidates[0], "BCS_UNDERLYING"
                ), ""
            if len(candidates) > 1:
                return None, "EXPLICIT_UNDERLYING_AMBIGUOUS"
            return None, "EXPLICIT_UNDERLYING_NOT_IN_SPOT"

        text = self.mapping_service._search_text(future)
        matches = self.mapping_service._match_spots(text, spots, spot_index)
        if len(matches) == 1:
            return self.mapping_service._result(
                future, matches[0], "SPOT_METADATA"
            ), ""
        if len(matches) > 1:
            return None, "TEXT_MATCH_AMBIGUOUS"
        return None, "NO_UNDERLYING_METADATA"

    @staticmethod
    def _metadata_snapshot(future):
        """Keep diagnostics compact while exposing every likely BCS field."""
        keys = (
            "ticker",
            "classCode",
            "name",
            "shortName",
            "displayName",
            "baseAsset",
            "baseAssetFuture",
            "baseAssetSecurity",
            "baseAssetSecuritySecCode",
            "baseAssetSecurityClassCode",
            "underlyingTicker",
            "underlyingSecurityCode",
            "underlyingSecurity",
            "underlyingAsset",
            "underlyingAssetTicker",
            "spotTicker",
            "spot_ticker",
        )
        return {
            key: future.get(key)
            for key in keys
            if future.get(key) not in (None, "", [], {})
        }
