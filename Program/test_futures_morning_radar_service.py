from datetime import date, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from services.futures_morning_radar_service import FuturesMorningRadarService


class FakeAPI:
    access_token = "test"


class FakeMappingService:
    def __init__(self, mappings): self.mappings = mappings
    def load(self): return list(self.mappings)


class FakeRadarService:
    def __init__(self, errors=None): self.errors = set(errors or [])
    def analyze(self, ticker, class_code):
        if ticker in self.errors: raise RuntimeError("test radar failure")
        long = ticker == "SBER"
        return {
            "status": "OK", "direction": "LONG" if long else "SHORT",
            "radar_score": 78.0 if long else 61.0,
            "relative_strength": 0.031 if long else -0.012,
            "relative_strength_status": "OK", "average_daily_money": 10_000_000_000,
            "change_percent": 1.2 if long else -0.8, "spot_price": 300.0 if long else 7000.0,
            "spot_group": "MOEX_STOCK", "signal": "LONG_WATCH" if long else "SHORT_WATCH",
        }


class FakeHistoryService:
    MOSCOW_TZ = ZoneInfo("Europe/Moscow")
    def __init__(self): self.trade_service = SimpleNamespace(api=FakeAPI())
    def now(self):
        from datetime import datetime
        return datetime(2026, 8, 26, 12, 0, tzinfo=self.MOSCOW_TZ)


class FakeSessionService:
    def get_session(self): return "MAIN"
    def get_trading_day(self): return date(2026, 8, 26)
    def now(self):
        from datetime import datetime
        return datetime(2026, 8, 26, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))


class FakeMoneyService:
    def calculate(self, ticker, class_code, **kwargs):
        return {"session": "MAIN", "money_volume": 2_000_000_000 if ticker == "SBER" else 1_000_000_000,
                "elapsed_minutes": 120, "expected_minutes": 540, "money_per_minute": 10_000_000}


class FakeSetupService:
    def __init__(self, state="READY"): self.state = state
    def analyze(self, ticker, class_code, **kwargs):
        direction = "LONG" if ticker == "SBER" else "SHORT"
        return {"setup": "FIRST_PULLBACK" if direction == "LONG" else "FIRST_REBOUND",
                "setup_direction": direction, "setup_state": self.state, "setup_phase": "SETUP_READY",
                "setup_quality_score": 70.0, "entry_trigger": 301.0 if direction == "LONG" else 6999.0,
                "previous_high": 301.0, "previous_low": 299.0, "impulse_percent": 1.0,
                "retracement_percent": 50.0, "retracement_ratio": 0.5, "consolidation_candles": 2,
                "impulse_high": 302.0, "impulse_low": 298.0}


class FakePriceStabilityService:
    def __init__(self, event_risk=False): self.event_risk = event_risk
    def evaluate(self, *args, **kwargs):
        return {"moex_event_risk": self.event_risk, "moex_price_stability_state": "NORMAL", "moex_data_status": "OK"}


def mappings():
    expiry = (date(2026, 8, 26) + timedelta(days=30)).isoformat()
    return [
        {"futures_ticker": "SRU6", "futures_class_code": "SPBFUT", "futures_expiry": expiry, "spot_ticker": "SBER", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK", "mapping_method": "EXPLICIT"},
        {"futures_ticker": "LKU6", "futures_class_code": "SPBFUT", "futures_expiry": expiry, "spot_ticker": "LKOH", "spot_class_code": "TQBR", "spot_group": "MOEX_STOCK", "mapping_method": "EXPLICIT"},
    ]


def make_service(mapping_list=None, setup_state="READY", errors=None, event_risk=False):
    service = FuturesMorningRadarService(api=FakeAPI(), mapping_service=FakeMappingService(mapping_list or mappings()),
        radar_service=FakeRadarService(errors), history_service=FakeHistoryService(), session_service=FakeSessionService(),
        session_money_service=FakeMoneyService(), spot_setup_service=FakeSetupService(setup_state))
    service.price_stability_service = FakePriceStabilityService(event_risk)
    return service


def test_ready_spot_gets_post_readiness_mapping():
    result = make_service().scan()
    assert [x["spot_ticker"] for x in result] == ["SBER", "LKOH"]
    assert result[0]["futures_ticker"] == "SRU6"
    assert result[0]["futures_selection_reason"] == "POST_SPOT_READINESS_MAPPING"


def test_wait_spot_is_ranked_but_not_mapped():
    result = make_service(setup_state="WAIT").scan()
    assert len(result) == 2
    assert all(x["futures_ticker"] == "" for x in result)
    assert all(x["futures_selection_reason"] == "WAITING_FOR_SPOT_READINESS" for x in result)


def test_event_risk_blocks_before_mapping():
    assert make_service(event_risk=True).scan() == []


def test_radar_error_does_not_stop_remaining_spot_scan():
    result = make_service(errors={"SBER"}).scan()
    assert [x["spot_ticker"] for x in result] == ["LKOH"]


def test_limit_is_applied_after_spot_ranking():
    result = make_service().scan(limit=1)
    assert len(result) == 1 and result[0]["spot_ticker"] == "SBER"


def test_expiring_contract_is_not_attached():
    data = mappings()
    data[0]["futures_expiry"] = (date(2026, 8, 26) + timedelta(days=2)).isoformat()
    result = make_service(data).scan()
    sber = next(x for x in result if x["spot_ticker"] == "SBER")
    assert sber["futures_ticker"] == ""


def test_candidate_score_is_spot_derived():
    result = make_service().scan()
    assert all(isinstance(x["candidate_score"], float) for x in result)
    assert result[0]["candidate_score"] >= result[1]["candidate_score"]
