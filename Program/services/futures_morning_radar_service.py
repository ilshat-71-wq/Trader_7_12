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


class FuturesMorningRadarService:
    """Build the current-session futures shortlist through the SPOT-first radar."""

    VERSION = "0.8"
    MAX_CONTRACTS_PER_SPOT = 2
    MAPPING_CACHE_SECONDS = 300

    def __init__(self, api=None, mapping_service=None, radar_service=None, history_service=None, session_service=None, session_money_service=None, spot_setup_service=None):
        self.api = api
        self.mapping_service = mapping_service or FuturesSpotMappingService(api=self.api)
        self.radar_service = radar_service or InstrumentMorningRadarService()
        self.history_service = history_service or HistoryCandleService()
        self.session_service = session_service or MarketSessionService()
        self.session_money_service = session_money_service or SessionMoneyVolumeService(history_service=self.history_service, session_service=self.session_service)
        self.spot_setup_service = spot_setup_service or SpotFirstPullbackService(self.history_service, self.session_service)
        self._mapping_cache = None
        self._mapping_cache_at = 0.0

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

    def scan(self, mappings=None, limit=None):
        """Run SPOT radar and attach current-session money, setup and activity."""
        if mappings is None:
            mappings=self._load_mappings_cached()
        if not isinstance(mappings,list): return []
        mappings=self._select_current_contracts(mappings)
        results=[]; radar_cache={}; money_cache={}; setup_cache={}
        session=self.session_service.get_session(); trading_date=self.session_service.get_trading_day()

        for mapping in mappings:
            if not isinstance(mapping,dict): continue
            futures_ticker=str(mapping.get("futures_ticker") or "").strip().upper()
            futures_class_code=str(mapping.get("futures_class_code") or "").strip()
            spot_ticker=str(mapping.get("spot_ticker") or "").strip().upper()
            spot_class_code=str(mapping.get("spot_class_code") or "").strip()
            if not futures_ticker or not spot_ticker or not spot_class_code: continue
            radar_key=(spot_ticker,spot_class_code)

            if radar_key not in radar_cache:
                try:
                    radar_cache[radar_key]=self.radar_service.analyze(spot_ticker,spot_class_code)
                except Exception as exc:
                    radar_cache[radar_key]={"version":self.VERSION,"status":"ERROR","error":str(exc)}
            radar=radar_cache[radar_key]
            if not isinstance(radar,dict): continue
            if str(radar.get("status","")).upper()=="ERROR":
                results.append({"version":self.VERSION,"status":"ERROR","error":radar.get("error","Radar analysis failed"),"futures_ticker":futures_ticker,"futures_class_code":futures_class_code,"futures_expiry":mapping.get("futures_expiry"),"spot_ticker":spot_ticker,"spot_class_code":spot_class_code,"spot_name":mapping.get("spot_name",""),"spot_type":mapping.get("spot_type",""),"mapping_method":mapping.get("mapping_method")})
                continue

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
                "futures_ticker":futures_ticker,
                "futures_class_code":futures_class_code,
                "futures_expiry":mapping.get("futures_expiry"),
                "spot_ticker":spot_ticker,
                "spot_class_code":spot_class_code,
                "spot_name":mapping.get("spot_name",""),
                "spot_type":mapping.get("spot_type",""),
                "mapping_method":mapping.get("mapping_method"),
                "market_session":session,
                "spot_money_volume":round(current_spot_money,2),
                "spot_average_daily_money":round(average_spot_money,2),
                "spot_money_ratio":round(spot_money_ratio,4),
                "spot_session_activity_ratio":spot_session_activity_ratio,
                "spot_money_per_minute":round(float(session_money.get("money_per_minute",0) or 0),2),
                "session_elapsed_minutes":elapsed_minutes,
                "session_expected_minutes":expected_minutes,
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
            results.append(result)

        results.sort(key=self._sort_key,reverse=True)
        for rank,result in enumerate(results,start=1): result["rank"]=rank
        if limit is not None:
            try: limit=int(limit)
            except (TypeError,ValueError): raise TypeError("limit must be an integer or None")
            if limit<0: raise ValueError("limit must be >= 0")
            return results[:limit]
        return results

    @classmethod
    def _select_current_contracts(cls,mappings):
        grouped={}
        for mapping in mappings:
            if not isinstance(mapping,dict): continue
            spot_ticker=str(mapping.get("spot_ticker") or "").strip().upper()
            if not spot_ticker: continue
            expiry=cls._parse_expiry(mapping.get("futures_expiry"))
            if expiry is None or expiry<date.today(): continue
            candidate=dict(mapping); candidate["futures_expiry"]=expiry.isoformat(); grouped.setdefault(spot_ticker,[]).append(candidate)
        selected=[]
        for candidates in grouped.values():
            candidates.sort(key=lambda item:(cls._parse_expiry(item.get("futures_expiry")) or date.max,str(item.get("futures_ticker") or "")))
            selected.extend(candidates[:cls.MAX_CONTRACTS_PER_SPOT])
        return sorted(selected,key=lambda item:(str(item.get("spot_ticker") or ""),cls._parse_expiry(item.get("futures_expiry")) or date.max,str(item.get("futures_ticker") or "")))

    @staticmethod
    def _parse_expiry(value):
        if value is None: return None
        if isinstance(value,date): return value
        text=str(value).strip()
        if not text: return None
        try: return date.fromisoformat(text[:10])
        except ValueError: return None

    @staticmethod
    def _sort_key(item):
        status=str(item.get("status","ERROR")).upper()
        try: money=float(item.get("spot_money_volume",0) or 0)
        except (TypeError,ValueError): money=0.0
        try: activity=float(item.get("spot_session_activity_ratio",0) or 0)
        except (TypeError,ValueError): activity=0.0
        try: setup=float(item.get("setup_quality_score",0) or 0)
        except (TypeError,ValueError): setup=0.0
        try: radar_score=float(item.get("radar_score",0) or 0)
        except (TypeError,ValueError): radar_score=0.0
        return (1,setup,activity,money,radar_score) if status=="OK" else (0,setup,activity,money,radar_score)

    @staticmethod
    def print_results(results):
        print(); print("="*160); print("TRADER_7_12 PRO - SPOT IMPULSE -> FIRST PULLBACK/REBOUND -> FUTURES"); print("="*160); print()
        print(f"{'RANK':<6}{'FUTURES':<12}{'SPOT':<9}{'MONEY':>16}{'PACE':>8}{'SETUP':<17}{'STATE':<12}{'RETR':>7}{'QUALITY':>9}{'DIR':<8}{'SESSION'}")
        print("-"*160)
        for item in results:
            print(f"{item.get('rank','-'): <6}{item.get('futures_ticker','-'): <12}{item.get('spot_ticker','-'): <9}{float(item.get('spot_money_volume',0) or 0):>16,.0f}{float(item.get('spot_session_activity_ratio',0) or 0):>8.2f}{str(item.get('setup','-')):<17}{str(item.get('setup_state','-')):<12}{float(item.get('retracement_ratio',0) or 0):>7.2f}{float(item.get('setup_quality_score',0) or 0):>9.1f}{str(item.get('direction','-')):<8}{item.get('market_session','-')}")
        print(); print("SPOT is the source of setup/market structure. FUTURES is the tradable instrument."); print("The service does not place orders or choose the user's exact entry."); print("="*160)
