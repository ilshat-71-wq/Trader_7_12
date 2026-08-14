"""
Trader_7_12 Pro

Futures Morning Radar Service

Stage 3 of the Spot-first architecture.

Purpose:
- connect the dynamic futures universe to Futures -> SPOT mapping;
- run the existing InstrumentMorningRadarService on the mapped SPOT assets;
- return one ordered shortlist where every radar result still points to its
  source futures contract.

Architecture:
    FuturesUniverseService
        -> FuturesSpotMappingService
        -> InstrumentMorningRadarService
        -> Futures Morning Radar candidates

This service is an orchestration layer only.
It does not contain trading-entry logic and does not place orders.
"""

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.instrument_morning_radar_service import InstrumentMorningRadarService


class FuturesMorningRadarService:
    """Build the current futures shortlist through the SPOT-first radar."""

    VERSION = "0.1"

    def __init__(self, mapping_service=None, radar_service=None):
        self.mapping_service = (
            mapping_service or FuturesSpotMappingService()
        )
        self.radar_service = (
            radar_service or InstrumentMorningRadarService()
        )

    def scan(self, mappings=None, limit=None):
        """
        Run Morning Radar for every uniquely mapped SPOT.

        ``mappings`` may be supplied by tests or by a later caller. When it
        is omitted, the dynamic Futures -> SPOT mapping service is used.
        """
        if mappings is None:
            mappings = self.mapping_service.load()

        if not isinstance(mappings, list):
            return []

        results = []

        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue

            futures_ticker = str(
                mapping.get("futures_ticker") or ""
            ).strip().upper()
            futures_class_code = str(
                mapping.get("futures_class_code") or ""
            ).strip()
            spot_ticker = str(
                mapping.get("spot_ticker") or ""
            ).strip().upper()
            spot_class_code = str(
                mapping.get("spot_class_code") or ""
            ).strip()

            if not futures_ticker or not spot_ticker:
                continue

            if not spot_class_code:
                continue

            try:
                radar = self.radar_service.analyze(
                    spot_ticker,
                    spot_class_code
                )
            except Exception as exc:
                results.append({
                    "version": self.VERSION,
                    "status": "ERROR",
                    "error": str(exc),
                    "futures_ticker": futures_ticker,
                    "futures_class_code": futures_class_code,
                    "spot_ticker": spot_ticker,
                    "spot_class_code": spot_class_code,
                    "mapping_method": mapping.get("mapping_method"),
                })
                continue

            if not isinstance(radar, dict):
                continue

            result = dict(radar)
            result.update({
                "pipeline_version": self.VERSION,
                "futures_ticker": futures_ticker,
                "futures_class_code": futures_class_code,
                "futures_expiry": mapping.get("futures_expiry"),
                "spot_ticker": spot_ticker,
                "spot_class_code": spot_class_code,
                "spot_name": mapping.get("spot_name", ""),
                "mapping_method": mapping.get("mapping_method"),
            })

            results.append(result)

        results.sort(
            key=self._sort_key,
            reverse=True
        )

        for rank, result in enumerate(results, start=1):
            result["rank"] = rank

        if limit is not None:
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                raise TypeError("limit must be an integer or None")

            if limit < 0:
                raise ValueError("limit must be >= 0")

            return results[:limit]

        return results

    @staticmethod
    def _sort_key(item):
        """Keep successful radar candidates ahead of errors."""
        status = str(item.get("status", "ERROR")).upper()

        try:
            radar_score = float(item.get("radar_score", 0) or 0)
        except (TypeError, ValueError):
            radar_score = 0.0

        if status == "OK":
            return (1, radar_score)

        return (0, radar_score)

    @staticmethod
    def print_results(results):
        print()
        print("=" * 110)
        print("TRADER_7_12 PRO - FUTURES MORNING RADAR")
        print("=" * 110)
        print()
        print(
            f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}"
            f"{'DIR':<8}{'RADAR':<9}{'RS':<10}"
            f"{'SIGNAL':<15}STATUS"
        )
        print("-" * 110)

        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('futures_ticker', '-'): <12}"
                f"{item.get('spot_ticker', '-'): <9}"
                f"{item.get('direction', '-'): <8}"
                f"{float(item.get('radar_score', 0) or 0):>7.2f}  "
                f"{float(item.get('relative_strength', 0) or 0):>8.4f} "
                f"{item.get('signal', '-'): <15}"
                f"{item.get('status', '-')}"
            )

        print()
        print("Pipeline: FUTURES -> SPOT -> Morning Radar")
        print("No trade execution is performed by this service.")
        print("=" * 110)
