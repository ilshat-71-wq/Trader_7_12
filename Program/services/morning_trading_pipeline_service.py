"""Session-aware SPOT-first scanner pipeline.

TOP-2/3 answers: "Which base assets deserve attention now?"
It is not an entry gate. Setup state is reported separately so WAIT/WATCH
assets can remain visible while READY/CONFIRMED assets are distinguished.
"""

from api.bcs_api import BCSAPI
from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.market_session_service import MarketSessionService


class MorningTradingPipelineService:
    """Rank base assets from SPOT data; futures remain user-selected separately."""

    VERSION = "1.0"
    SESSION_PROFILES = {
        "MORNING": {"candidate": 0.70, "activity": 0.20, "momentum": 0.10, "label": "ИМПУЛЬС / АКТИВНОСТЬ / ПЕРВЫЙ ДВИЖ"},
        "MAIN": {"candidate": 0.65, "activity": 0.25, "momentum": 0.10, "label": "ПРОДОЛЖЕНИЕ / СИЛА-СЛАБОСТЬ / АКТИВНОСТЬ"},
        "EVENING": {"candidate": 0.60, "activity": 0.25, "momentum": 0.15, "label": "ВЕЧЕРНИЙ ИМПУЛЬС / СИЛА-СЛАБОСТЬ / АКТИВНОСТЬ"},
    }

    def __init__(self, radar_service=None, confirmation_service=None, candidate_service=None, session_service=None):
        self.session_service = session_service or MarketSessionService()
        api = None
        if radar_service is None:
            api = BCSAPI()
            if not api.authorize():
                raise RuntimeError("BCS API authorization failed")
        self.radar_service = radar_service or TwoPhaseFuturesMorningRadarService(api=api)
        self.confirmation_service = None
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
        return str(candidate.get("setup_state") or "WAIT").upper()

    def scan(self, mappings=None, confirmations=None, limit=3):
        session_info = self.session_service.get_session_info()
        session = session_info.get("session", "CLOSED")
        if session not in {"MORNING", "MAIN", "EVENING"}:
            self._last_scan_diagnostics = {"session": session, "radar_results": 0, "candidates": 0, "selected": 0, "ready": 0, "confirmed": 0, "watch": 0, "wait": 0}
            return []

        radar_results = self.radar_service.scan(mappings=mappings)
        candidates = self.candidate_service.rank(radar_results, confirmations=None, limit=None)
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

        # TOP-2/3 is an opportunity ranking, not an entry gate.
        # WAIT/WATCH assets remain visible; setup formation is a separate stage.
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
            "ready": sum(1 for item in candidates if self._setup_state(item) == "READY"),
            "confirmed": sum(1 for item in candidates if self._setup_state(item) == "CONFIRMED"),
            "watch": sum(1 for item in candidates if self._setup_state(item) == "WATCH"),
            "wait": sum(1 for item in candidates if self._setup_state(item) == "WAIT"),
        }
        if selected:
            selected[0]["scan_diagnostics"] = dict(self._last_scan_diagnostics)
        return selected

    @staticmethod
    def print_results(results):
        print()
        print("=" * 118)
        print("TRADER_7_12 PRO - SPOT-FIRST OPPORTUNITY WATCHLIST")
        print("=" * 118)
        print()
        print(f"{'RANK':<6}{'SPOT':<14}{'DIR':<8}{'OPPORTUNITY':>13}{'SETUP':>9}{'PACE':>9}{'RS':>9}{'SPOT MONEY':>18}")
        print("-" * 118)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}{item.get('spot_ticker', '-'): <14}{item.get('direction', '-'): <8}"
                f"{float(item.get('opportunity_score', item.get('session_rank_score', 0)) or 0):>13.2f}"
                f"{str(item.get('setup_state', '-')).upper():>9}"
                f"{float(item.get('spot_session_activity_ratio', 0) or 0):>9.2f}"
                f"{float(item.get('relative_strength', 0) or 0):>9.2f}"
                f"{float(item.get('spot_money_volume', 0) or 0):>18,.0f}"
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
                    f"READY={diagnostics.get('ready', 0)} "
                    f"CONFIRMED={diagnostics.get('confirmed', 0)} "
                    f"WATCH={diagnostics.get('watch', 0)} "
                    f"WAIT={diagnostics.get('wait', 0)}"
                )
        else:
            print("NO WATCHLIST CANDIDATES")
        print()
        print("Pipeline: FAST SPOT SCREEN -> DEEP SPOT H1/RS/M5 -> TOP 2-3 BASE ASSETS")
        print("TOP-2/3 = watchlist ranking; SETUP STATE is reported separately and is not a trade command.")
        print("Futures are NOT analyzed or used for confirmation, ranking, direction or RS.")
        print("User independently selects the futures contract and decides whether/where to enter.")
        print("Scanner output is read-only and contains no portfolio or order operations.")
        print("=" * 118)
