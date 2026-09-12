from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_session_service import MarketSessionService
from services.market_attention_scanner_service import MarketAttentionScannerService


MSK = ZoneInfo("Europe/Moscow")


def msk(value):
    return datetime.fromisoformat(value).replace(tzinfo=MSK)


def test_non_trading_weekend_is_closed():
    service = MarketSessionService()
    assert service.get_session(msk("2026-09-12T10:00:00")) == "CLOSED"
    assert service.get_session(msk("2026-09-13T10:00:00")) == "CLOSED"
    assert service.is_market_open(msk("2026-09-12T10:00:00")) is False
    assert service.is_market_open(msk("2026-09-13T10:00:00")) is False


def test_weekend_trading_session_is_not_treated_as_closed():
    service = MarketSessionService()
    value = msk("2026-09-19T10:00:00")
    assert service.get_session(value) == "WEEKEND_SESSION"
    assert service.get_session_start(value).isoformat() == "09:50:00"
    assert service.is_market_open(value) is True


def test_pre_open_is_distinct_from_closed():
    service = MarketSessionService()
    value = msk("2026-09-14T06:55:00")
    assert service.get_session(value) == "PRE_OPEN"
    assert service.get_session_start(value).isoformat() == "06:55:00" if False else service.get_session_start(value) is None
    assert service.is_market_open(value) is False


def test_regular_sessions_have_expected_boundaries():
    service = MarketSessionService()
    assert service.get_session(msk("2026-09-14T07:00:00")) == "MORNING"
    assert service.get_session(msk("2026-09-14T09:59:59")) == "MORNING"
    assert service.get_session(msk("2026-09-14T10:00:00")) == "MAIN"
    assert service.get_session(msk("2026-09-14T18:59:59")) == "MAIN"
    assert service.get_session(msk("2026-09-14T19:00:00")) == "EVENING"
    assert service.get_session(msk("2026-09-14T23:49:59")) == "EVENING"
    assert service.get_session(msk("2026-09-14T23:50:00")) == "CLOSED"


def test_market_regime_neutral_does_not_create_direction():
    service = object.__new__(MarketAttentionScannerService)
    assert service._market_regime(0.09) == "NEUTRAL"
    assert service._market_regime(-0.09) == "NEUTRAL"
    assert service._market_regime(0.10) == "UP"
    assert service._market_regime(-0.10) == "DOWN"


def test_liquidity_gate_requires_both_paces():
    service = object.__new__(MarketAttentionScannerService)
    assert service._liquidity_ok({"money_per_minute": 8000, "recent_money_per_minute": 5000}) is True
    assert service._liquidity_ok({"money_per_minute": 7999, "recent_money_per_minute": 9000}) is False
    assert service._liquidity_ok({"money_per_minute": 9000, "recent_money_per_minute": 4999}) is False


def test_percentile_is_deterministic_and_bounded():
    service = MarketAttentionScannerService
    assert service._percentile(10, []) == 0.0
    assert service._percentile(10, [10]) == 100.0
    assert service._percentile(10, [0, 10, 20]) == 50.0
    assert 0.0 <= service._percentile(10, [1, 2, 3, 4]) <= 100.0
