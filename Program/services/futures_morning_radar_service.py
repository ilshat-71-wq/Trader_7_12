"""
Trader_7_12 Pro

Futures Morning Radar Service

Stage 3 of the Spot-first architecture.
"""

from datetime import date
import time

from services.futures_spot_mapping_service import FuturesSpotMappingService
from services.instrument_morning_radar_service import InstrumentMorningRadarService
from services.history_candle_service import HistoryCandleService
from services.market_session_service import MarketSessionService
from services.session_money_volume_service import SessionMoneyVolumeService
from services.spot_first_pullback_service import SpotFirstPullbackService
from services.moex_price_stability_service import MoexPriceStabilityService
from services.futures_trade_candidate_service import FuturesTradeCandidateService


class FuturesMorningRadarService:
    """Build the current-session SPOT shortlist, then attach futures mapping."""

    VERSION = "1.2"
    MAX_CONTRACTS_PER_SPOT = 2
    MAX_DAYS_TO_EXPIRY = 3
    MAPPING_CACHE_SECONDS = 300

    def __init__(self, api=None, mapping_service=None, radar_service=None, history_service=None, session_service=None, session_money_service=None, spot_setup_service=None):
        self.api = api
        self.mapping_service = mapping_service or FuturesSpotMappingService(api=self.api)
        self.radar_service = radar_service or InstrumentMorningRadarService()
        self.history_service = history_service or HistoryCandleService()
        self.session_service = session_service or MarketSessionService()
        self.session_money_service = session_money_service or SessionMoneyVolumeService(history_service=self.history_service, session_service=self.session_service)
        self.spot_setup_service = spot_setup_service or SpotFirstPullbackService(self.history_service, self.session_service)
        stability_api = self.api
        if stability_api is None:
            trade_service = getattr(self.history_service, "trade_service", None)
            stability_api = getattr(trade_service, "api", None)
        self.price_stability_service = MoexPriceStabilityService(api=stability_api)
        self._mapping_cache = None
        self._mapping_cache_at = 0.0
        self._price_stability_cache = {}

    @staticmethod
    def _activity_ratio(current_money, average_daily_money, elapsed_minutes, expected_minutes):
        try:
            current=float(current_money or 0); average=float(average_daily_money or 0); elapsed=float(elapsed_minutes or 0); expected=float(expected_minutes or 0)
        except (TypeError, ValueError):
            return 0.0
        if current<=0 or average<=0 or elapsed<=0 or expected<=0: return 0.0
        expected_to_now=average*(elapsed/expected)
        if expected_to_now<=0: return 0.0
        return round(current/expected_to_now,4)

    def _load_mappings_cached(self):
        now=time.monotonic()
        if self._mapping_cache is not None and now-self._mapping_cache_at < self.MAPPING_CACHE_SECONDS:
            return list(self._mapping_cache)
        mappings=self.mapping_service.load()
        if isinstance(mappings,list):
            self._mapping_cache=list(mappings)
            self._mapping_cache_at=now
        return mappings

    def _price_stability(self, spot_ticker, spot_class_code, reference_close, trading_date):
        key=(spot_ticker, spot_class_code, round(float(reference_close or 0), 8), str(trading_date))
        if key in self._price_stability_cache:
            return dict(self._price_stability_cache[key])
        try:
            result=self.price_stability_service.evaluate(
                spot_ticker,
                spot_class_code,
                reference_close=reference_close,
                trading_date=trading_date,
                now=self.session_service.now(),
            )
        except Exception as exc:
            result={
                "moex_event_risk": False,
                "moex_price_stability_state": "ERROR",
                "moex_price_stability_reason": type(exc).__name__,
                "moex_data_status": "ERROR",
            }
        self._price_stability_cache[key]=dict(result)
        return dict(result)

    @staticmethod
    def _spot_mapping_groups(mappings):
        grouped={}
        for mapping in mappings or []:
            if not isinstance(mapping,dict):
                continue
            spot_ticker=str(mapping.get("spot_ticker") or "").strip().upper()
            spot_class_code=str(mapping.get("spot_class_code") or "").strip()
            if not spot_ticker or not spot_class_code:
                continue
            grouped.setdefault((spot_ticker,spot_class_code),[]).append(mapping)
        return grouped

    @classmethod
    def _spot_ready_for_mapping(cls, result):
        """Allow futures mapping only for direction-consistent ready SPOT setups."""
        direction=str(result.get("direction") or "NONE").upper()
        setup=str(result.get("setup") or "NONE").upper()
        setup_direction=str(result.get("setup_direction") or direction).upper()
        state=str(result.get("setup_state") or "WAIT").upper()
        try:
            trigger=float(result.get("entry_trigger",0) or 0)
            price=float(result.get("spot_price",result.get("last_close",0)) or 0)
        except (TypeError,ValueError):
            return False
        return (
            direction in {"LONG","SHORT"}
            and setup_direction == direction
            and setup != "NONE"
            and state in {"READY","CONFIRMED"}
            and trigger > 0
            and price > 0
        )

    @classmethod
    def _select_current_contracts(cls,mappings):
        """Return non-expiring contracts for post-readiness mapping only."""
        grouped={}
        today=date.today()
        for mapping in mappings or []:
            if not isinstance(mapping,dict): continue
            spot_ticker=str(mapping.get("spot_ticker") or "").strip().upper()
            if not spot_ticker: continue
            expiry=cls._parse_expiry(mapping.get("futures_expiry"))
            if expiry is None: continue
            days_to_expiry=(expiry-today).days
            if days_to_expiry <= cls.MAX_DAYS_TO_EXPIRY: continue
            candidate=dict(mapping)
            candidate["futures_expiry"]=expiry.isoformat()
            candidate["days_to_expiry"]=days_to_expiry
            grouped.setdefault(spot_ticker,[]).append(candidate)
        selected=[]
        for candidates in grouped.values():
            candidates.sort(key=lambda item:(cls._parse_expiry(item.get("futures_expiry")) or date.max,str(item.get("futures_ticker")or "")))
            selected.extend(candidates[:cls.MAX_CONTRACTS_PER_SPOT])
        return sorted(selected,key=lambda item:(str(item.get("spot_ticker") or ""),cls._parse_expiry(item.get("futures_expiry")) or date.max,str(item.get("futures_ticker") or "")))

    @classmethod
    def _select_futures_mapping(cls, mappings):
        """Choose a futures reference only after the SPOT setup is ready."""
        eligible=cls._select_current_contracts(mappings)
        return eligible[0] if eligible else None

    @staticmethod
    def _parse_expiry(value):
        if value is None: return None
        if isinstance(value,date): return value
        text=str(value).strip()
        if not text: return None
        try: return date.fromisoformat(text[:10])
        except ValueError: return None

    def scan(self, mappings=None, limit=None):
        """Run the complete SPOT analysis first; futures are mapping-only afterwards."""
        if mappings is None:
            mappings=self._load_mappings_cached()
        if not isinstance(mappings,list): return []

        grouped=self._spot_mapping_groups(mappings)
        results=[]; radar_cache={}; money_cache={}; setup_cache={}
        session=self.session_service.get_session(); trading_date=self.session_service.get_trading_day()

        for radar_key, spot_mappings in grouped.items():
            spot_ticker,spot_class_code=radar_key
            representative=spot_mappings[0]
            if radar_key not in radar_cache:
                try:
                    radar_cache[radar_key]=self.radar_service.analyze(spot_ticker,spot_class_code)
                except Exception as exc:
                    radar_cache[radar_key]={"version":self.VERSION,"status":"ERROR","error":str(exc)}
            radar=radar_cache[radar_key]
            if not isinstance(radar,dict): continue
            if str(radar.get("status","")).upper()=="ERROR":
                continue

            price_stability=self._price_stability(spot_ticker,spot_class_code,radar.get("last_close",0),trading_date)
            if radar_key not in setup_cache:
                try:
                    setup_cache[radar_key]=self.spot_setup_service.analyze(spot_ticker,spot_class_code,direction=radar.get("direction"),session=session,trading_date=trading_date)
                except Exception as exc:
                    setup_cache[radar_key]={"setup":"NONE","setup_direction":radar.get("direction","NONE"),"setup_state":"WAIT","setup_phase":"SETUP_ERROR","setup_quality_score":0.0,"setup_error":str(exc)}
            spot_setup=setup_cache[radar_key]

            if radar_key not in money_cache:
                try:
                    money_cache[radar_key]=self.session_money_service.calculate(spot_ticker,spot_class_code,trading_date=trading_date,timeframe_minutes=5,session=session)
                except Exception:
                    money_cache[radar_key]={"session":session,"money_volume":0.0,"elapsed_minutes":0,"expected_minutes":0,"money_per_minute":0.0}
            session_money=money_cache[radar_key]
            current_spot_money=float(session_money.get("money_volume",0) or 0)
            average_spot_money=float(radar.get("average_daily_money",0) or 0)
            elapsed_minutes=int(session_money.get("elapsed_minutes",0) or 0)
            expected_minutes=int(session_money.get("expected_minutes",0) or 0)
            spot_money_ratio=current_spot_money/average_spot_money if average_spot_money>0 else 0.0
            spot_session_activity_ratio=self._activity_ratio(current_spot_money,average_spot_money,elapsed_minutes,expected_minutes)

            result=dict(radar)
            result.update({
                "pipeline_version":self.VERSION,
                "futures_ticker":"",
                "futures_class_code":"",
                "futures_expiry":None,
                "days_to_expiry":None,
                "selection_score":None,
                "liquidity_score":None,
                "spread_score":None,
                "expiry_score":None,
                "spread_percent":None,
                "turnover_30m":None,
                "trade_count_30m":None,
                "depth_notional":None,
                "bid":None,
                "ask":None,
                "last":None,
                "futures_selection_version":None,
                "futures_selection_reason":"WAITING_FOR_SPOT_READINESS",
                "futures_selection_candidates":None,
                "spot_ticker":spot_ticker,
                "spot_class_code":spot_class_code,
                "spot_name":representative.get("spot_name",""),
                "spot_type":representative.get("spot_type",""),
                "mapping_method":representative.get("mapping_method"),
                "market_session":session,
                "spot_money_volume":round(current_spot_money,2),
                "spot_average_daily_money":round(average_spot_money,2),
                "spot_money_ratio":round(spot_money_ratio,4),
                "spot_session_activity_ratio":spot_session_activity_ratio,
                "spot_money_per_minute":round(float(session_money.get("money_per_minute",0) or 0),2),
                "session_elapsed_minutes":elapsed_minutes,
                "session_expected_minutes":expected_minutes,
                "moex_event_risk":bool(price_stability.get("moex_event_risk")),
                "moex_da_trigger_inferred":bool(price_stability.get("moex_da_trigger_inferred")),
                "moex_da_trigger_percent":float(price_stability.get("moex_da_trigger_percent",20.0) or 20.0),
                "moex_da_window_minutes":int(price_stability.get("moex_da_window_minutes",10) or 10),
                "moex_weekend_band_percent":float(price_stability.get("moex_weekend_band_percent",3.0) or 3.0),
                "moex_weekend_band_near":bool(price_stability.get("moex_weekend_band_near")),
                "moex_weekend_band_hit":bool(price_stability.get("moex_weekend_band_hit")),
                "moex_max_abs_move_percent":float(price_stability.get("moex_max_abs_move_percent",0.0) or 0.0),
                "moex_price_stability_state":price_stability.get("moex_price_stability_state","NORMAL"),
                "moex_price_stability_reason":price_stability.get("moex_price_stability_reason",""),
                "moex_candles_loaded":int(price_stability.get("moex_candles_loaded",0) or 0),
                "moex_data_status":price_stability.get("moex_data_status","NO_DATA"),
                "setup":spot_setup.get("setup",radar.get("setup","NONE")),
                "setup_direction":spot_setup.get("setup_direction",radar.get("setup_direction",radar.get("direction","NONE"))),
                "setup_state":spot_setup.get("setup_state",radar.get("setup_state","WAIT")),
                "setup_phase":spot_setup.get("setup_phase","UNKNOWN"),
                "setup_quality_score":float(spot_setup.get("setup_quality_score",0) or 0),
                "impulse_percent":float(spot_setup.get("impulse_percent",0) or 0),
                "retracement_percent":float(spot_setup.get("retracement_percent",0) or 0),
                "retracement_ratio":float(spot_setup.get("retracement_ratio",0) or 0),
                "consolidation_candles":int(spot_setup.get("consolidation_candles",0) or 0),
                "entry_trigger":float(spot_setup.get("entry_trigger",radar.get("entry_trigger",0)) or 0),
                "previous_high":float(spot_setup.get("previous_high",radar.get("previous_high",0)) or 0),
                "previous_low":float(spot_setup.get("previous_low",radar.get("previous_low",0)) or 0),
                "impulse_high":float(spot_setup.get("impulse_high",0) or 0),
                "impulse_low":float(spot_setup.get("impulse_low",0) or 0),
            })

            # Canonical SPOT eligibility/ranking gate. This is deliberately
            # evaluated before any futures mapping is attached.
            candidate = FuturesTradeCandidateService.build_candidate(result)
            if candidate is None:
                continue
            result["candidate_score"] = candidate["candidate_score"]

            # Critical architectural boundary: no futures lookup/selection is
            # performed until the SPOT candidate has passed eligibility and
            # the SPOT setup is READY/CONFIRMED with a usable trigger.
            if self._spot_ready_for_mapping(result):
                selected=self._select_futures_mapping(spot_mappings)
                if selected:
                    result.update({
                        "futures_ticker":selected.get("futures_ticker",""),
                        "futures_class_code":selected.get("futures_class_code",""),
                        "futures_expiry":selected.get("futures_expiry"),
                        "days_to_expiry":selected.get("days_to_expiry"),
                        "selection_score":selected.get("selection_score"),
                        "liquidity_score":selected.get("liquidity_score"),
                        "spread_score":selected.get("spread_score"),
                        "expiry_score":selected.get("expiry_score"),
                        "spread_percent":selected.get("spread_percent"),
                        "turnover_30m":selected.get("turnover_30m"),
                        "trade_count_30m":selected.get("trade_count_30m"),
                        "depth_notional":selected.get("depth_notional"),
                        "bid":selected.get("bid"),
                        "ask":selected.get("ask"),
                        "last":selected.get("last"),
                        "futures_selection_version":selected.get("futures_selection_version"),
                        "futures_selection_reason":selected.get("futures_selection_reason","POST_SPOT_READINESS_MAPPING"),
                        "futures_selection_candidates":selected.get("futures_selection_candidates"),
                        "mapping_method":selected.get("mapping_method",result.get("mapping_method")),
                    })
            results.append(result)

        results.sort(key=self._sort_key,reverse=True)
        for rank,result in enumerate(results,start=1): result["rank"]=rank
        if limit is not None:
            try: limit=int(limit)
            except (TypeError,ValueError): raise TypeError("limit must be an integer or None")
            if limit<0: raise ValueError("limit must be >= 0")
            return results[:limit]
        return results

    @staticmethod
    def _sort_key(item):
        direction=str(item.get("direction") or "").upper()
        rs=float(item.get("relative_strength",0) or 0)
        directional_rs=rs if direction=="LONG" else -rs if direction=="SHORT" else 0.0
        return (
            float(item.get("candidate_score",0) or 0),
            float(item.get("spot_session_activity_ratio",0) or 0),
            float(item.get("spot_money_per_minute",0) or 0),
            float(item.get("spot_money_volume",0) or 0),
            directional_rs,
            float(item.get("setup_quality_score",0) or 0),
            str(item.get("spot_ticker") or ""),
        )

    @staticmethod
    def print_results(results):
        print(); print("="*160); print("TRADER_7_12 PRO - SPOT IMPULSE -> FIRST PULLBACK/REBOUND -> FUTURES MAPPING"); print("="*160); print()
        print(f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}{'SCORE':>8}{'MONEY':>16}{'PACE':>8}{'SETUP':<17}{'STATE':<12}{'RETR':>7}{'QUALITY':>9}{'DIR':<8}{'SESSION'}")
        print("-"*160)
        for item in results:
            print(f"{item.get('rank','-'): <6}{item.get('futures_ticker','-'): <12}{item.get('spot_ticker','-'): <9}{float(item.get('candidate_score',0) or 0):>8.2f}{float(item.get('spot_money_volume',0) or 0):>16,.0f}{float(item.get('spot_session_activity_ratio',0) or 0):>8.2f}{str(item.get('setup','-')):<17}{str(item.get('setup_state','-')):<12}{float(item.get('retracement_ratio',0) or 0):>7.2f}{float(item.get('setup_quality_score',0) or 0):>9.1f}{str(item.get('direction','-')):<8}{item.get('market_session','-')}")
        print(); print("SPOT is the source of eligibility, score, setup/market structure/readiness. FUTURES is attached only afterwards as the tradable instrument."); print("MOEX-style price-instability fields are derived from authenticated BCS SPOT candles."); print("The service does not place orders or choose the user's exact entry."); print("="*160)
