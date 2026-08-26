"""Session-aware SPOT-first scanner pipeline.

The pipeline answers one question: which BASE ASSETS deserve attention now?
Direction, setup, trigger and readiness are SPOT properties. Futures mapping is
reference-only and never confirms, blocks, ranks or changes a SPOT idea.
"""

from api.bcs_api import BCSAPI
from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.market_session_service import MarketSessionService


class MorningTradingPipelineService:
    """Build the read-only chain: direction -> setup -> trigger -> readiness -> futures mapping."""

    VERSION = "1.2"
    SESSION_PROFILES = {
        "MORNING": {"candidate": 0.70, "activity": 0.20, "momentum": 0.10, "label": "ИМПУЛЬС / АКТИВНОСТЬ / ПЕРВЫЙ ДВИЖ"},
        "MAIN": {"candidate": 0.65, "activity": 0.25, "momentum": 0.10, "label": "ПРОДОЛЖЕНИЕ / СИЛА-СЛАБОСТЬ / АКТИВНОСТЬ"},
        "EVENING": {"candidate": 0.60, "activity": 0.25, "momentum": 0.15, "label": "ВЕЧЕРНИЙ ИМПУЛЬС / СИЛА-СЛАБОСТЬ / АКТИВНОСТЬ"},
    }
    VALID_SETUPS = {"FIRST_PULLBACK", "FIRST_REBOUND", "BREAKOUT", "PULLBACK", "REBOUND"}
    VALID_STATES = {"WAIT", "WATCH", "READY", "CONFIRMED"}

    def __init__(self, radar_service=None, confirmation_service=None, candidate_service=None, session_service=None):
        self.session_service = session_service or MarketSessionService()
        api = None
        if radar_service is None:
            api = BCSAPI()
            if not api.authorize():
                raise RuntimeError("BCS API authorization failed")
        self.radar_service = radar_service or TwoPhaseFuturesMorningRadarService(api=api)
        # Kept only for backwards-compatible construction. It is deliberately
        # not used: futures are mapping-only in the canonical architecture.
        self.confirmation_service = confirmation_service
        self.candidate_service = candidate_service or FuturesTradeCandidateService()
        self._last_scan_diagnostics = {}

    @classmethod
    def _session_rank_score(cls, candidate, session):
        profile = cls.SESSION_PROFILES.get(session, cls.SESSION_PROFILES["MAIN"])

        def bounded(key):
            try:
                return max(0.0, min(100.0, float(candidate.get(key, 0) or 0)))
            except (TypeError, ValueError):
                return 0.0

        candidate_score = bounded("candidate_score")
        try:
            activity_ratio = max(0.0, float(candidate.get("spot_session_activity_ratio", 0) or 0))
        except (TypeError, ValueError):
            activity_ratio = 0.0
        activity_score = min(100.0, activity_ratio * 50.0)
        direction = str(candidate.get("direction") or "").upper()
        try:
            change = float(candidate.get("spot_change_percent", 0) or 0)
        except (TypeError, ValueError):
            change = 0.0
        directional_change = change if direction == "LONG" else -change if direction == "SHORT" else 0.0
        momentum_score = min(100.0, max(0.0, directional_change * 25.0))
        return round(candidate_score * profile["candidate"] + activity_score * profile["activity"] + momentum_score * profile["momentum"], 2)

    @staticmethod
    def _setup_score(candidate):
        try:
            return round(max(0.0, min(100.0, float(candidate.get("setup_quality_score", 0) or 0))), 2)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _setup_state(candidate):
        state = str(candidate.get("setup_state") or "WAIT").upper()
        return state if state in MorningTradingPipelineService.VALID_STATES else "WAIT"

    @staticmethod
    def _trigger_present(candidate):
        try:
            trigger = float(candidate.get("entry_trigger", 0) or 0)
            price = float(candidate.get("spot_price", candidate.get("last_close", 0)) or 0)
        except (TypeError, ValueError):
            return False
        return trigger > 0 and price > 0

    @classmethod
    def _advance_signal_state(cls, candidate):
        """Derive readiness exclusively from the SPOT setup and trigger.

        WATCH + valid trigger -> READY.
        SPOT CONFIRMED + valid trigger -> CONFIRMED.
        No futures request is made here.
        """
        setup_state = cls._setup_state(candidate)
        setup = str(candidate.get("setup") or "NONE").upper()
        direction = str(candidate.get("direction") or "NONE").upper()
        trigger_present = cls._trigger_present(candidate)

        candidate["signal_state"] = "WAIT"
        candidate["signal_state_reason"] = "SPOT setup is not ready"
        candidate["futures_confirmation"] = "NOT_APPLICABLE"
        candidate["futures_confirmation_status"] = "MAPPING_ONLY"
        candidate["futures_confirmation_score"] = 0
        candidate["futures_confirmation_reason"] = "Futures are reference-only; confirmation is not part of the SPOT signal"

        if direction not in {"LONG", "SHORT"} or setup not in cls.VALID_SETUPS:
            return
        if not trigger_present:
            return

        if setup_state == "CONFIRMED":
            candidate["signal_state"] = "CONFIRMED"
            candidate["signal_state_reason"] = "SPOT setup and trigger are confirmed by SPOT price structure"
        elif setup_state in {"WATCH", "READY"}:
            candidate["signal_state"] = "READY"
            candidate["signal_state_reason"] = "SPOT setup is armed and has a real trigger"

    def scan(self, mappings=None, confirmations=None, limit=3):
        session_info = self.session_service.get_session_info()
        session = session_info.get("session", "CLOSED")
        if session not in {"MORNING", "MAIN", "EVENING"}:
            self._last_scan_diagnostics = {"session": session, "radar_results": 0, "candidates": 0, "selected": 0, "ready": 0, "confirmed": 0, "watch": 0, "wait": 0}
            return []

        radar_results = self.radar_service.scan(mappings=mappings)
        candidates = self.candidate_service.rank(radar_results, confirmations=confirmations, limit=None)
        profile = self.SESSION_PROFILES.get(session, self.SESSION_PROFILES["MAIN"])

        for candidate in candidates:
            candidate["market_session"] = session
            candidate["market_session_label"] = session_info.get("label", session)
            candidate["market_timezone"] = session_info.get("timezone", "Europe/Moscow")
            candidate["market_date"] = session_info.get("date")
            candidate["market_time"] = session_info.get("time")
            candidate["session_strategy"] = profile["label"]
            candidate["session_rank_score"] = self._session_rank_score(candidate, session)
            candidate["opportunity_score"] = candidate["session_rank_score"]
            candidate["setup_score"] = self._setup_score(candidate)
            candidate["setup_state"] = self._setup_state(candidate)
            candidate["selection_role"] = "TOP_WATCHLIST"
            self._advance_signal_state(candidate)

        candidates.sort(key=lambda item: (
            item.get("opportunity_score", 0),
            item.get("candidate_score", 0),
            item.get("spot_session_activity_ratio", 0),
            item.get("relative_strength", 0),
            item.get("spot_money_volume", 0),
        ), reverse=True)

        selected = candidates[:max(0, int(limit or 0))]
        for rank, candidate in enumerate(selected, start=1):
            candidate["pipeline_version"] = self.VERSION
            candidate["rank"] = rank

        self._last_scan_diagnostics = {
            "session": session,
            "radar_results": len(radar_results),
            "candidates": len(candidates),
            "selected": len(selected),
            "ready": sum(1 for item in candidates if item.get("signal_state") == "READY"),
            "confirmed": sum(1 for item in candidates if item.get("signal_state") == "CONFIRMED"),
            "watch": sum(1 for item in candidates if self._setup_state(item) == "WATCH"),
            "wait": sum(1 for item in candidates if self._setup_state(item) == "WAIT"),
        }
        if selected:
            selected[0]["scan_diagnostics"] = dict(self._last_scan_diagnostics)
        return selected

    @staticmethod
    def print_results(results):
        print()
        print("=" * 128)
        print("TRADER_7_12 PRO - SPOT DIRECTION -> SETUP -> TRIGGER -> READINESS -> FUTURES MAPPING")
        print("=" * 128)
        print()
        print(f"{'RANK':<6}{'SPOT':<12}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<17}{'TRIGGER':>12}")
        print("-" * 128)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}{item.get('spot_ticker', '-'): <12}{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}{str(item.get('setup', '-')):<17}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
            )
        if results:
            first = results[0]
            diagnostics = first.get("scan_diagnostics")
            print()
            print(f"SESSION: {first.get('market_session_label', first.get('market_session', '-'))}")
            print(f"TIME: {first.get('market_date', '-')} {first.get('market_time', '-')} MSK")
            print(f"STRATEGY: {first.get('session_strategy', '-')}")
            if diagnostics:
                print(
                    "DIAGNOSTICS: "
                    f"RADAR={diagnostics.get('radar_results', 0)} "
                    f"CANDIDATES={diagnostics.get('candidates', 0)} "
                    f"SELECTED={diagnostics.get('selected', 0)} "
                    f"READY={diagnostics.get('ready', 0)} "
                    f"CONFIRMED={diagnostics.get('confirmed', 0)} "
                    f"WATCH={diagnostics.get('watch', 0)} "
                    f"WAIT={diagnostics.get('wait', 0)}"
                )
        else:
            print("NO WATCHLIST CANDIDATES")
        print()
        print("Pipeline: FAST SPOT SCREEN -> DEEP SPOT H1/RS/M5 -> SETUP/TRIGGER -> READINESS -> FUTURES MAPPING")
        print("Direction, setup, trigger and readiness are determined from SPOT only.")
        print("READY = valid SPOT setup + real trigger; CONFIRMED = SPOT setup itself confirmed by SPOT structure.")
        print("Futures are mapping-only and never change eligibility, direction, RS, setup, readiness or ranking.")
        print("Scanner output is read-only and contains no portfolio sizing, SL/TP or order execution.")
        print("=" * 128)
