"""Session-aware SPOT-first scanner pipeline.

TOP-2/3 answers: "Which base assets deserve attention now?"
Signal state is derived from SPOT setup/trigger first; selected futures are
used only as the final directional confirmation gate.
"""

from api.bcs_api import BCSAPI
from services.two_phase_futures_morning_radar_service import TwoPhaseFuturesMorningRadarService
from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.futures_confirmation_service import FuturesConfirmationService
from services.market_session_service import MarketSessionService


class MorningTradingPipelineService:
    """Build the complete read-only signal chain: direction -> setup -> trigger -> futures."""

    VERSION = "1.1"
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
        if confirmation_service is not None:
            self.confirmation_service = confirmation_service
        else:
            radar_api = getattr(getattr(self.radar_service, "mapping_service", None), "api", None)
            self.confirmation_service = FuturesConfirmationService(api=radar_api) if radar_api is not None else None
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

    @staticmethod
    def _trigger_present(candidate):
        try:
            trigger = float(candidate.get("entry_trigger", 0) or 0)
            price = float(candidate.get("spot_price", candidate.get("last_close", 0)) or 0)
        except (TypeError, ValueError):
            return False
        return trigger > 0 and price > 0

    def _advance_signal_state(self, candidate):
        """Advance state without allowing futures to change SPOT direction/setup."""
        setup_state = self._setup_state(candidate)
        trigger_present = self._trigger_present(candidate)
        setup = str(candidate.get("setup") or "NONE").upper()
        direction = str(candidate.get("direction") or "NONE").upper()

        candidate["signal_state"] = "WAIT"
        candidate["signal_state_reason"] = "SPOT setup is not armed"
        candidate["futures_confirmation"] = "NOT_CHECKED"
        candidate["futures_confirmation_status"] = "NOT_CHECKED"
        candidate["futures_confirmation_score"] = 0
        candidate["futures_confirmation_reason"] = ""

        # A WATCH/CONFIRMED SPOT setup with a real trigger is an actionable
        # READY state. The original setup state is preserved for diagnostics.
        if direction in {"LONG", "SHORT"} and setup in {"FIRST_PULLBACK", "FIRST_REBOUND", "BREAKOUT", "PULLBACK", "REBOUND"} and trigger_present and setup_state in {"WATCH", "CONFIRMED", "READY"}:
            candidate["signal_state"] = "READY"
            candidate["signal_state_reason"] = "SPOT setup and trigger are armed; waiting for futures confirmation"
        elif setup_state == "CONFIRMED" and trigger_present:
            candidate["signal_state"] = "READY"
            candidate["signal_state_reason"] = "SPOT setup confirmed; waiting for futures confirmation"
        else:
            return

        confirmation = self.confirmation_service
        if confirmation is None:
            candidate["futures_confirmation"] = "NO_DATA"
            candidate["futures_confirmation_status"] = "NO_DATA"
            candidate["futures_confirmation_reason"] = "Futures confirmation service unavailable"
            return

        futures_ticker = candidate.get("futures_ticker")
        futures_class_code = candidate.get("futures_class_code")
        if not futures_ticker or not futures_class_code:
            candidate["futures_confirmation"] = "NO_DATA"
            candidate["futures_confirmation_status"] = "NO_DATA"
            candidate["futures_confirmation_reason"] = "Selected futures contract is unavailable"
            return

        try:
            result = confirmation.analyze(futures_ticker, futures_class_code, direction)
        except Exception as exc:
            candidate["futures_confirmation"] = "NO_DATA"
            candidate["futures_confirmation_status"] = "NO_DATA"
            candidate["futures_confirmation_reason"] = f"{type(exc).__name__}: {exc}"
            return

        candidate["futures_confirmation"] = result.get("confirmation", "NO_DATA")
        candidate["futures_confirmation_status"] = result.get("status", "NO_DATA")
        candidate["futures_confirmation_score"] = int(result.get("score", 0) or 0)
        candidate["futures_confirmation_reason"] = result.get("reason", "")
        candidate["futures_trade_count"] = int(result.get("trade_count", 0) or 0)
        candidate["futures_money_volume"] = float(result.get("money_volume", 0) or 0)
        candidate["futures_price_change_percent"] = float(result.get("price_change_percent", 0) or 0)
        candidate["futures_last_price"] = float(result.get("last_price", 0) or 0)

        if str(result.get("status") or "").upper() == "OK" and str(result.get("confirmation") or "").upper() == "CONFIRMED":
            candidate["signal_state"] = "CONFIRMED"
            candidate["signal_state_reason"] = "SPOT setup/trigger confirmed by the selected futures contract"
        elif str(result.get("status") or "").upper() == "BLOCKED":
            candidate["signal_state"] = "BLOCKED"
            candidate["signal_state_reason"] = result.get("reason", "Futures confirmation blocked")

    def scan(self, mappings=None, confirmations=None, limit=3):
        session_info = self.session_service.get_session_info()
        session = session_info.get("session", "CLOSED")
        if session not in {"MORNING", "MAIN", "EVENING"}:
            self._last_scan_diagnostics = {"session": session, "radar_results": 0, "candidates": 0, "selected": 0, "ready": 0, "confirmed": 0, "blocked": 0, "watch": 0, "wait": 0}
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
            "blocked": sum(1 for item in candidates if item.get("signal_state") == "BLOCKED"),
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
        print("TRADER_7_12 PRO - SPOT DIRECTION -> SETUP -> TRIGGER -> FUTURES CONFIRMATION")
        print("=" * 128)
        print()
        print(f"{'RANK':<6}{'SPOT':<12}{'DIR':<8}{'SIGNAL':<12}{'SETUP':<17}{'TRIGGER':>12}{'FUTURES':<12}{'FUT CONF':<12}")
        print("-" * 128)
        for item in results:
            print(
                f"{item.get('rank', '-'): <6}{item.get('spot_ticker', '-'): <12}{item.get('direction', '-'): <8}"
                f"{item.get('signal_state', 'WAIT'): <12}{str(item.get('setup', '-')):<17}"
                f"{float(item.get('entry_trigger', 0) or 0):>12.4f}"
                f"{str(item.get('futures_ticker', '-')):<12}{str(item.get('futures_confirmation', 'NOT_CHECKED')):<12}"
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
                    f"BLOCKED={diagnostics.get('blocked', 0)} "
                    f"WATCH={diagnostics.get('watch', 0)} "
                    f"WAIT={diagnostics.get('wait', 0)}"
                )
        else:
            print("NO WATCHLIST CANDIDATES")
        print()
        print("Pipeline: FAST SPOT SCREEN -> DEEP SPOT H1/RS/M5 -> SETUP/TRIGGER -> FUTURES CONFIRMATION")
        print("Direction and setup are determined from SPOT. Futures can only CONFIRM or BLOCK the existing SPOT idea.")
        print("READY = valid SPOT setup + real trigger; CONFIRMED = READY + futures confirmation.")
        print("Scanner output is read-only and contains no portfolio sizing, SL/TP or order execution.")
        print("=" * 128)
