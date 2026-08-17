"""
Trader_7_12 Pro

Futures Morning Radar Service

Stage 3 of the Spot-first architecture.

Purpose:
- connect the dynamic futures universe to Futures -> SPOT mapping;
- keep the two nearest non-expired futures contracts per SPOT underlying;
- run the existing SPOT Morning Radar on each unique SPOT;
- attach current-session SPOT money/activity to every mapped futures candidate;
- return an ordered shortlist where every radar result points to its
  corresponding futures contract.

The trading instrument remains the futures contract. SPOT current money is
used to identify where today's market attention is concentrated before
futures confirmation/ranking.
"""

from datetime import date

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.instrument_morning_radar_service import InstrumentMorningRadarService
from services.history_candle_service import HistoryCandleService
from services.market_session_service import MarketSessionService
from services.session_money_volume_service import SessionMoneyVolumeService


class FuturesMorningRadarService:
    """Build the current-session futures shortlist through the SPOT-first radar."""

    VERSION = "0.5"
    MAX_CONTRACTS_PER_SPOT = 2

    def __init__(self, mapping_service=None, radar_service=None, history_service=None, session_service=None, session_money_service=None):
        self.mapping_service = mapping_service or FuturesSpotMappingService()
        self.radar_service = radar_service or InstrumentMorningRadarService()
        self.history_service = history_service or HistoryCandleService()
        self.session_service = session_service or MarketSessionService()
        self.session_money_service = session_money_service or SessionMoneyVolumeService(
            history_service=self.history_service,
            session_service=self.session_service,
        )

    def scan(self, mappings=None, limit=None):
        """Run SPOT radar and attach money/activity for the active Moscow session."""
        if mappings is None:
            mappings = self.mapping_service.load()

        if not isinstance(mappings, list):
            return []

        mappings = self._select_current_contracts(mappings)
        results = []
        radar_cache = {}
        money_cache = {}
        session = self.session_service.get_session()
        trading_date = self.session_service.get_trading_day()

        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue

            futures_ticker = str(mapping.get("futures_ticker") or "").strip().upper()
            futures_class_code = str(mapping.get("futures_class_code") or "").strip()
            spot_ticker = str(mapping.get("spot_ticker") or "").strip().upper()
            spot_class_code = str(mapping.get("spot_class_code") or "").strip()

            if not futures_ticker or not spot_ticker or not spot_class_code:
                continue

            radar_key = (spot_ticker, spot_class_code)
            if radar_key not in radar_cache:
                try:
                    radar_cache[radar_key] = self.radar_service.analyze(
                        spot_ticker,
                        spot_class_code,
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

            if str(radar.get("status", "")).upper() == "ERROR":
                results.append({
                    "version": self.VERSION,
                    "status": "ERROR",
                    "error": radar.get("error", "Radar analysis failed"),
                    "futures_ticker": futures_ticker,
                    "futures_class_code": futures_class_code,
                    "futures_expiry": mapping.get("futures_expiry"),
                    "spot_ticker": spot_ticker,
                    "spot_class_code": spot_class_code,
                    "spot_name": mapping.get("spot_name", ""),
                    "spot_type": mapping.get("spot_type", ""),
                    "mapping_method": mapping.get("mapping_method"),
                })
                continue

            if radar_key not in money_cache:
                try:
                    money_cache[radar_key] = self.session_money_service.calculate(
                        spot_ticker,
                        spot_class_code,
                        trading_date=trading_date,
                        timeframe_minutes=5,
                        session=session,
                    )
                except Exception:
                    money_cache[radar_key] = {
                        "session": session,
                        "money_volume": 0.0,
                        "elapsed_minutes": 0,
                        "expected_minutes": 0,
                        "money_per_minute": 0.0,
                    }

            session_money = money_cache[radar_key]
            current_spot_money = float(session_money.get("money_volume", 0) or 0)
            average_spot_money = float(radar.get("average_daily_money", 0) or 0)
            spot_money_ratio = (
                current_spot_money / average_spot_money
                if average_spot_money > 0
                else 0.0
            )

            result = dict(radar)
            result.update({
                "pipeline_version": self.VERSION,
                "futures_ticker": futures_ticker,
                "futures_class_code": futures_class_code,
                "futures_expiry": mapping.get("futures_expiry"),
                "spot_ticker": spot_ticker,
                "spot_class_code": spot_class_code,
                "spot_name": mapping.get("spot_name", ""),
                "spot_type": mapping.get("spot_type", ""),
                "mapping_method": mapping.get("mapping_method"),
                "market_session": session,
                "spot_money_volume": round(current_spot_money, 2),
                "spot_average_daily_money": round(average_spot_money, 2),
                "spot_money_ratio": round(spot_money_ratio, 4),
                "spot_money_per_minute": round(float(session_money.get("money_per_minute", 0) or 0), 2),
                "session_elapsed_minutes": int(session_money.get("elapsed_minutes", 0) or 0),
                "session_expected_minutes": int(session_money.get("expected_minutes", 0) or 0),
            })
            results.append(result)

        results.sort(key=self._sort_key, reverse=True)

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
            if expiry is None or expiry < date.today():
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
        status = str(item.get("status", "ERROR")).upper()
        try:
            money = float(item.get("spot_money_volume", 0) or 0)
        except (TypeError, ValueError):
            money = 0.0
        try:
            ratio = float(item.get("spot_money_ratio", 0) or 0)
        except (TypeError, ValueError):
            ratio = 0.0
        try:
            radar_score = float(item.get("radar_score", 0) or 0)
        except (TypeError, ValueError):
            radar_score = 0.0
        if status == "OK":
            return (1, money, ratio, radar_score)
        return (0, money, ratio, radar_score)

    @staticmethod
    def print_results(results):
        print()
        print("=" * 130)
        print("TRADER_7_12 PRO - SPOT MONEY -> FUTURES SESSION RADAR")
        print("=" * 130)
        print()
        print(
            f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}"
            f"{'MONEY':>16}{'AVG MONEY':>16}{'RATIO':>9}"
            f"{'EXPIRY':<12}{'DIR':<8}{'RADAR':>8}  SESSION"
        )
        print("-" * 130)

        for item in results:
            print(
                f"{item.get('rank', '-'): <6}"
                f"{item.get('futures_ticker', '-'): <12}"
                f"{item.get('spot_ticker', '-'): <9}"
                f"{float(item.get('spot_money_volume', 0) or 0):>16,.0f}"
                f"{float(item.get('spot_average_daily_money', 0) or 0):>16,.0f}"
                f"{float(item.get('spot_money_ratio', 0) or 0):>9.2f}"
                f"{item.get('futures_expiry', '-'): <12}"
                f"{item.get('direction', '-'): <8}"
                f"{float(item.get('radar_score', 0) or 0):>7.2f}  "
                f"{item.get('market_session', '-')}"
            )

        print()
        print("Current SPOT money = M5 price x volume from session start to current Moscow time.")
        print("No trade execution is performed by this service.")
        print("=" * 130)
