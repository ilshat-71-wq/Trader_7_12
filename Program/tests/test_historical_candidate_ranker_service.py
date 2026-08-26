from services.futures_trade_candidate_service import FuturesTradeCandidateService
from services.futures_morning_radar_service import FuturesMorningRadarService
from services.historical_candidate_ranker_service import HistoricalCandidateRankerService


def test_futures_fields_do_not_change_historical_score():
    base = {
        "direction": "LONG", "trend_state": "UPTREND", "trend_change_percent": 2.0,
        "relative_strength_available": True, "relative_strength_data": {"excess_change_percent": 1.5},
        "relative_strength": 15.0, "setup": "FIRST_PULLBACK", "setup_state": "READY",
        "entry_trigger": 100.0, "spot_setup_state": "READY", "spot_entry_trigger": 100.0,
        "spot_ready_time": "08:30:00", "average_daily_money": 300_000_000,
        "futures_average_daily_money": 100_000_000, "futures_price": 100.0,
        "futures_confirmation": {"status": "OK", "score": 100},
    }
    changed = dict(base)
    changed.update({"futures_average_daily_money": 9_999_999_999, "futures_price": 999.0,
                    "futures_confirmation": {"status": "BLOCKED", "score": 0}, "confirmation_time": "12:55:00"})
    assert HistoricalCandidateRankerService.score(base) == HistoricalCandidateRankerService.score(changed)


def test_spot_readiness_changes_historical_score():
    wait = {"direction": "LONG", "trend_state": "UPTREND", "trend_change_percent": 2.0,
            "relative_strength_available": True, "relative_strength_data": {"excess_change_percent": 1.0},
            "setup": "FIRST_PULLBACK", "setup_state": "WAIT", "entry_trigger": 0.0,
            "average_daily_money": 300_000_000}
    ready = dict(wait)
    ready.update({"setup_state": "READY", "entry_trigger": 100.0, "spot_setup_state": "READY",
                  "spot_entry_trigger": 100.0, "spot_ready_time": "08:30:00"})
    assert HistoricalCandidateRankerService.score(ready) > HistoricalCandidateRankerService.score(wait)


def test_production_candidate_score_ignores_futures_confirmation():
    base = {"direction": "SHORT", "spot_group": "MOEX_STOCK", "relative_strength": -1.5,
            "relative_strength_status": "OK", "spot_session_activity_ratio": 2.0,
            "spot_money_per_minute": 20_000_000, "spot_money_volume": 400_000_000,
            "change_percent": -2.0, "setup_quality_score": 60.0,
            "futures_average_daily_money": 100_000_000, "futures_price": 100.0,
            "futures_confirmation": {"status": "OK", "score": 100}}
    changed = dict(base)
    changed.update({"futures_average_daily_money": 9_999_999_999, "futures_price": 999.0,
                    "futures_confirmation": {"status": "BLOCKED", "score": 0}})
    assert FuturesTradeCandidateService.calculate_score(base) == FuturesTradeCandidateService.calculate_score(changed)


def test_production_rank_tie_breaks_relative_strength_in_trade_direction(monkeypatch):
    service = FuturesTradeCandidateService()
    radars = [
        {"direction": "SHORT", "spot_group": "MOEX_STOCK", "spot_ticker": "WEAK_A",
         "spot_session_activity_ratio": 2.0, "spot_money_per_minute": 20_000_000,
         "spot_money_volume": 400_000_000, "relative_strength": -1.0,
         "relative_strength_status": "OK", "setup_quality_score": 50.0},
        {"direction": "SHORT", "spot_group": "MOEX_STOCK", "spot_ticker": "WEAK_B",
         "spot_session_activity_ratio": 2.0, "spot_money_per_minute": 20_000_000,
         "spot_money_volume": 400_000_000, "relative_strength": -3.0,
         "relative_strength_status": "OK", "setup_quality_score": 50.0},
    ]
    def fixed_candidate(radar):
        return {"candidate_score": 80.0, "spot_session_activity_ratio": 2.0,
                "spot_money_per_minute": 20_000_000, "spot_money_volume": 400_000_000,
                "relative_strength": radar["relative_strength"], "direction": radar["direction"],
                "setup_quality_score": 50.0, "spot_ticker": radar["spot_ticker"]}
    monkeypatch.setattr(service, "build_candidate", fixed_candidate)
    ranked = service.rank(radars, limit=2)
    assert [item["spot_ticker"] for item in ranked] == ["WEAK_B", "WEAK_A"]


def test_historical_rank_tie_breaks_relative_strength_in_trade_direction():
    rows = [
        {"direction": "SHORT", "trend_state": "DOWNTREND", "trend_change_percent": 2.0,
         "relative_strength_available": True, "relative_strength_data": {"excess_change_percent": 1.0},
         "relative_strength": -1.0, "setup": "FIRST_REBOUND", "setup_state": "WATCH",
         "entry_trigger": 0.0, "average_daily_money": 300_000_000, "spot_ready_time": "08:30:00", "spot_ticker": "WEAK_A"},
        {"direction": "SHORT", "trend_state": "DOWNTREND", "trend_change_percent": 2.0,
         "relative_strength_available": True, "relative_strength_data": {"excess_change_percent": 1.0},
         "relative_strength": -3.0, "setup": "FIRST_REBOUND", "setup_state": "WATCH",
         "entry_trigger": 0.0, "average_daily_money": 300_000_000, "spot_ready_time": "08:30:00", "spot_ticker": "WEAK_B"},
    ]
    ranked = HistoricalCandidateRankerService.rank(rows, limit=2)
    assert [item["spot_ticker"] for item in ranked] == ["WEAK_B", "WEAK_A"]


def test_production_candidate_rejects_missing_relative_strength():
    radar = {"direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 0.0,
             "relative_strength_status": "UNAVAILABLE", "spot_session_activity_ratio": 5.0,
             "spot_money_per_minute": 50_000_000, "spot_money_volume": 1_000_000_000,
             "change_percent": 3.0, "setup_quality_score": 100.0}
    assert FuturesTradeCandidateService.build_candidate(radar) is None


def test_production_candidate_rejects_event_risk_even_with_strong_spot_signal():
    radar = {"direction": "SHORT", "spot_group": "MOEX_STOCK", "relative_strength": -3.0,
             "relative_strength_status": "OK", "moex_event_risk": True,
             "spot_session_activity_ratio": 5.0, "spot_money_per_minute": 50_000_000,
             "spot_money_volume": 1_000_000_000, "change_percent": -3.0,
             "setup_quality_score": 100.0}
    assert FuturesTradeCandidateService.build_candidate(radar) is None


class _FakeTradeService:
    api = None


class _FakeHistoryService:
    trade_service = _FakeTradeService()


class _FakeSessionService:
    def get_session(self): return "REGULAR"
    def get_trading_day(self): return "2026-08-26"
    def now(self): return "2026-08-26T10:00:00"


class _FakeRadarService:
    def __init__(self, radars): self.radars = radars
    def analyze(self, ticker, class_code): return dict(self.radars[ticker])


class _FakeSetupService:
    def __init__(self, setups): self.setups = setups
    def analyze(self, ticker, class_code, **kwargs): return dict(self.setups[ticker])


class _FakeMoneyService:
    def __init__(self, money): self.money = money
    def calculate(self, ticker, class_code, **kwargs): return dict(self.money[ticker])


class _FakeStabilityService:
    def evaluate(self, *args, **kwargs): return {"moex_event_risk": False, "moex_data_status": "OK"}


def test_production_scan_uses_candidate_score_not_setup_quality_for_ranking():
    radars = {
        "FAST": {"status": "OK", "direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 2.0,
                  "relative_strength_status": "OK", "average_daily_money": 300_000_000, "last_close": 100.0, "change_percent": 1.0},
        "QUALITY": {"status": "OK", "direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 0.5,
                     "relative_strength_status": "OK", "average_daily_money": 300_000_000, "last_close": 100.0, "change_percent": 1.0},
    }
    setups = {
        "FAST": {"setup": "FIRST_PULLBACK", "setup_state": "WAIT", "setup_phase": "WATCH", "setup_quality_score": 10.0},
        "QUALITY": {"setup": "FIRST_PULLBACK", "setup_state": "WAIT", "setup_phase": "WATCH", "setup_quality_score": 100.0},
    }
    money = {
        "FAST": {"money_volume": 900_000_000, "elapsed_minutes": 120, "expected_minutes": 420, "money_per_minute": 7_500_000},
        "QUALITY": {"money_volume": 150_000_000, "elapsed_minutes": 120, "expected_minutes": 420, "money_per_minute": 1_250_000},
    }
    mappings = [{"spot_ticker": "FAST", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK"},
                {"spot_ticker": "QUALITY", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK"}]
    service = FuturesMorningRadarService(mapping_service=object(), radar_service=_FakeRadarService(radars),
                                         history_service=_FakeHistoryService(), session_service=_FakeSessionService(),
                                         session_money_service=_FakeMoneyService(money), spot_setup_service=_FakeSetupService(setups))
    service.price_stability_service = _FakeStabilityService()
    ranked = service.scan(mappings=mappings, limit=2)
    assert [item["spot_ticker"] for item in ranked] == ["FAST", "QUALITY"]
    assert ranked[0]["candidate_score"] > ranked[1]["candidate_score"]


def test_production_scan_never_attaches_futures_before_spot_readiness():
    radars = {"WAITING": {"status": "OK", "direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 2.0,
                           "relative_strength_status": "OK", "average_daily_money": 300_000_000, "last_close": 100.0, "change_percent": 1.0}}
    setups = {"WAITING": {"setup": "FIRST_PULLBACK", "setup_state": "WAIT", "setup_phase": "WATCH",
                           "setup_quality_score": 50.0, "entry_trigger": 0.0}}
    money = {"WAITING": {"money_volume": 500_000_000, "elapsed_minutes": 120, "expected_minutes": 420, "money_per_minute": 4_166_666}}
    mappings = [{"spot_ticker": "WAITING", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK",
                 "futures_ticker": "FUTURE_SHOULD_NOT_BE_ATTACHED", "futures_class_code": "SPBFUT", "futures_expiry": "2026-12-20"}]
    service = FuturesMorningRadarService(mapping_service=object(), radar_service=_FakeRadarService(radars),
                                         history_service=_FakeHistoryService(), session_service=_FakeSessionService(),
                                         session_money_service=_FakeMoneyService(money), spot_setup_service=_FakeSetupService(setups))
    service.price_stability_service = _FakeStabilityService()
    ranked = service.scan(mappings=mappings, limit=1)
    assert ranked[0]["futures_ticker"] == ""
    assert ranked[0]["futures_selection_reason"] == "WAITING_FOR_SPOT_READINESS"


def test_production_scan_attaches_futures_only_after_ready_spot(monkeypatch):
    radars = {"READY": {"status": "OK", "direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 2.0,
                         "relative_strength_status": "OK", "average_daily_money": 300_000_000, "last_close": 100.0, "change_percent": 1.0}}
    setups = {"READY": {"setup": "FIRST_PULLBACK", "setup_state": "READY", "setup_phase": "TRIGGERED",
                         "setup_quality_score": 75.0, "entry_trigger": 101.0}}
    money = {"READY": {"money_volume": 700_000_000, "elapsed_minutes": 120, "expected_minutes": 420, "money_per_minute": 5_833_333}}
    mappings = [{"spot_ticker": "READY", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK",
                 "futures_ticker": "RI_REFERENCE", "futures_class_code": "SPBFUT", "futures_expiry": "2026-12-20"}]
    service = FuturesMorningRadarService(mapping_service=object(), radar_service=_FakeRadarService(radars),
                                         history_service=_FakeHistoryService(), session_service=_FakeSessionService(),
                                         session_money_service=_FakeMoneyService(money), spot_setup_service=_FakeSetupService(setups))
    service.price_stability_service = _FakeStabilityService()
    calls = []
    def select_mapping(spot_mappings):
        calls.append("mapped")
        return dict(spot_mappings[0])
    monkeypatch.setattr(service, "_select_futures_mapping", select_mapping)

    ranked = service.scan(mappings=mappings, limit=1)
    assert calls == ["mapped"]
    assert ranked[0]["futures_ticker"] == "RI_REFERENCE"
    assert ranked[0]["futures_selection_reason"] == "POST_SPOT_READINESS_MAPPING"


def test_production_scan_event_risk_blocks_candidate_before_futures_mapping(monkeypatch):
    radars = {"RISK": {"status": "OK", "direction": "LONG", "spot_group": "MOEX_STOCK", "relative_strength": 3.0,
                        "relative_strength_status": "OK", "average_daily_money": 300_000_000, "last_close": 100.0, "change_percent": 2.0}}
    setups = {"RISK": {"setup": "FIRST_PULLBACK", "setup_state": "READY", "setup_phase": "TRIGGERED",
                        "setup_quality_score": 100.0, "entry_trigger": 101.0}}
    money = {"RISK": {"money_volume": 900_000_000, "elapsed_minutes": 120, "expected_minutes": 420, "money_per_minute": 7_500_000}}
    mappings = [{"spot_ticker": "RISK", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK",
                 "futures_ticker": "FUTURE_BLOCKED", "futures_class_code": "SPBFUT", "futures_expiry": "2026-12-20"}]

    class _RiskStabilityService:
        def evaluate(self, *args, **kwargs):
            return {"moex_event_risk": True, "moex_data_status": "OK"}

    service = FuturesMorningRadarService(mapping_service=object(), radar_service=_FakeRadarService(radars),
                                         history_service=_FakeHistoryService(), session_service=_FakeSessionService(),
                                         session_money_service=_FakeMoneyService(money), spot_setup_service=_FakeSetupService(setups))
    service.price_stability_service = _RiskStabilityService()
    calls = []
    def select_mapping(spot_mappings):
        calls.append("mapped")
        return dict(spot_mappings[0])
    monkeypatch.setattr(service, "_select_futures_mapping", select_mapping)

    assert service.scan(mappings=mappings, limit=1) == []
    assert calls == []
