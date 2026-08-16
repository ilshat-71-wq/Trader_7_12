"""
Trader_7_12 Pro

Futures Morning Radar Service

Stage 3 of the Spot-first architecture.

Purpose:
- connect the dynamic futures universe to Futures -> SPOT mapping;
- keep the two nearest non-expired futures contracts per SPOT underlying;
- run the existing InstrumentMorningRadarService on each unique SPOT;
- return an ordered shortlist where every radar result points to its
  selected futures contract.

Architecture:
    FuturesUniverseService
        -> FuturesSpotMappingService
        -> FuturesMorningRadarService
        -> InstrumentMorningRadarService
        -> shortlist

This service is an orchestration layer only.
It does not contain trading-entry logic and does not place orders.
"""

from datetime import date

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.instrument_morning_radar_service import InstrumentMorningRadarService


class FuturesMorningRadarService:
    """Build the current futures shortlist through the SPOT-first radar."""

    VERSION = "0.3"
    MAX_CONTRACTS_PER_SPOT = 2

    def __init__(self, mapping_service=None, radar_service=None):
        self.mapping_service = (
            mapping_service or FuturesSpotMappingService()
        )
        self.radar_service = (
            radar_service or InstrumentMorningRadarService()
        )

    def scan(self, mappings=None, limit=None):
        """
        Run Morning Radar for the two nearest valid futures contracts per SPOT.

        SPOT Radar is calculated once per unique SPOT. The result is then
        attached to each of the selected futures contracts for that SPOT.
        """
        if mappings is None:
            mappings = self.mapping_service.load()

        if not isinstance(mappings, list):
            return []

        mappings = self._select_current_contracts(mappings)
        results = []

        # Calculate SPOT Radar only once per unique SPOT.
        radar_cache = {}

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

            if not futures_ticker or not spot_ticker or not spot_class_code:
                continue

            radar_key = (
                spot_ticker,
                spot_class_code,
            )

            if radar_key not in radar_cache:
                try:
                    radar_cache[radar_key] = (
                        self.radar_service.analyze(
                            spot_ticker,
                            spot_class_code
                        )
                    )
                except Exception as exc:
                    radar_cache[radar_key] = {
                        "version": self.VERSION,
                        "status": "ERROR",
                        "error": str(exc),
                    }

            radar = radar_cache[radar_key]

            if not isinstance(radar, dict):
                continue

            if str(
                radar.get("status", "")
            ).upper() == "ERROR":
                results.append({
                    "version": self.VERSION,
                    "status": "ERROR",
                    "error": radar.get(
                        "error",
                        "Radar analysis failed"
                    ),
                    "futures_ticker": futures_ticker,
                    "futures_class_code": futures_class_code,
                    "spot_ticker": spot_ticker,
                    "spot_class_code": spot_class_code,
                    "mapping_method": mapping.get(
                        "mapping_method"
                    ),
                })
                continue

            result = dict(radar)

            result.update({
                "pipeline_version": self.VERSION,
                "futures_ticker": futures_ticker,
                "futures_class_code": futures_class_code,
                "futures_expiry": mapping.get(
                    "futures_expiry"
                ),
                "spot_ticker": spot_ticker,
                "spot_class_code": spot_class_code,
                "spot_name": mapping.get(
                    "spot_name",
                    ""
                ),
                "mapping_method": mapping.get(
                    "mapping_method"
                ),
            })

            results.append(result)

        results.sort(
            key=self._sort_key,
            reverse=True
        )

        for rank, result in enumerate(
            results,
            start=1
        ):
            result["rank"] = rank

        if limit is not None:
            try:
                limit = int(limit)
            except (
                TypeError,
                ValueError
            ):
                raise TypeError(
                    "limit must be an integer or None"
                )

            if limit < 0:
                raise ValueError(
                    "limit must be >= 0"
                )

            return results[:limit]

        return results


    @classmethod
    def _select_current_contracts(cls, mappings):
        """Keep the two nearest valid futures contracts for each SPOT."""
        grouped = {}

        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue

            spot_ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            if not spot_ticker:
                continue

            expiry = cls._parse_expiry(mapping.get("futures_expiry"))
            if expiry is None:
                continue

            if expiry < date.today():
                continue

            candidate = dict(mapping)
            candidate["futures_expiry"] = expiry.isoformat()
            grouped.setdefault(spot_ticker, []).append(candidate)

        selected = []
        for candidates in grouped.values():
            candidates.sort(
                key=lambda item: (
                    cls._parse_expiry(item.get("futures_expiry")) or date.max,
                    str(item.get("futures_ticker") or ""),
                )
            )
            selected.extend(candidates[:cls.MAX_CONTRACTS_PER_SPOT])

        return sorted(
            selected,
            key=lambda item: (
                str(item.get("spot_ticker") or ""),
                cls._parse_expiry(item.get("futures_expiry")) or date.max,
                str(item.get("futures_ticker") or ""),
            )
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
            f"{'EXPIRY':<12}{'DIR':<8}{'RADAR':<9}{'RS':<10}"
            f"{'SIGNAL':<15}STATUS"
        )
        print("-" * 110)

        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('futures_ticker', '-'): <12}"
                f"{item.get('spot_ticker', '-'): <9}"
                f"{item.get('futures_expiry', '-'): <12}"
                f"{item.get('direction', '-'): <8}"
                f"{float(item.get('radar_score', 0) or 0):>7.2f}  "
                f"{float(item.get('relative_strength', 0) or 0):>8.4f} "
                f"{item.get('signal', '-'): <15}"
                f"{item.get('status', '-')}"
            )

        print()
        print("Pipeline: FUTURES -> SPOT -> Morning Radar")
        print("Two nearest futures contracts per SPOT are retained.")
        print("No trade execution is performed by this service.")
        print("=" * 110)
