from datetime import datetime, time
from zoneinfo import ZoneInfo

from services.market_attention_scanner_service import MarketAttentionScannerService


class FakeAPI:
    access_token = "ok"
    def authorize(self):
        return True


class FakeSession:
    TIMEZONE = ZoneInfo("Europe/Moscow")
    MORNING_START = time(7, 0)
    MAIN_START = time(10, 0)
    def now(self):
        return datetime(2026, 9, 2, 10, 0, tzinfo=self.TIMEZONE)
    def get_trading_day(self):
        return self.now().date()
    def get_session_info(self):
        return {"session": "MORNING"}
    def get_session_start(self, value=None):
        return self.MORNING_START
    def is_market_open(self, value=None):
        return True


class FakeWeekendSession(FakeSession):
    def now(self):
        return datetime(2026, 9, 5, 10, 44, tzinfo=self.TIMEZONE)
    def get_session_info(self):
        return {"session": "WEEKEND_SESSION"}
    def get_session_start(self, value=None):
        return time(9, 50)


class FakeAfternoonSession(FakeSession):
    def now(self):
        return datetime(2026, 9, 2, 14, 0, tzinfo=self.TIMEZONE)
    def get_session_info(self):
        return {"session": "MAIN"}
    def get_session_start(self, value=None):
        return self.MAIN_START


def _row(ticker, change, money, acceleration=0.0):
    return {"spot_ticker": ticker, "spot_class_code": "TQBR", "market_group": "STOCK", "change_percent": change,
            "session_money": money, "money_per_minute": money / 180.0, "recent_money": money / 3.0,
            "recent_money_per_minute": money / 45.0, "money_acceleration": acceleration, "data_status": "AVAILABLE"}


def _qualified_profile(direction="LONG"):
    return {"direction": direction, "qualified": True, "structure_direction": direction,
            "structure_state": "STRONG_STRUCTURE" if direction == "LONG" else "WEAK_STRUCTURE",
            "relative_direction": "STRONGER" if direction == "LONG" else "WEAKER",
            "relative_mean_pp": 0.5, "days": 3}


def _scanner(monkeypatch, rows, benchmark=0.0, session=None):
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=session or FakeSession(), history_service=object())
    monkeypatch.setattr(scanner, "build_universe", lambda: [dict(x) for x in rows])
    monkeypatch.setattr(scanner, "_benchmark", lambda *args: ("IMOEX2", "INDX", benchmark) if benchmark is not None else (None, None, None))
    monkeypatch.setattr(scanner, "_benchmark_daily", lambda *args: [{"time": "2026-08-31T00:00:00Z", "open": 100, "high": 101, "low": 99, "close": 100},
                                                                       {"time": "2026-09-01T00:00:00Z", "open": 100, "high": 101, "low": 99, "close": 100}])
    monkeypatch.setattr(scanner, "_analyze_one", lambda item, *args: dict(item))
    monkeypatch.setattr(scanner, "_daily_profile", lambda item, *args: _qualified_profile("LONG" if item["change_percent"] > benchmark else "SHORT"))
    return scanner


def test_strong_on_up_market_is_long(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("STRONG", 1.8, 2_000_000), _row("WEAK", 0.2, 1_900_000)], 0.7)
    result = scanner.scan(limit=2)
    assert result[0]["selection_role"] == "LONG_CANDIDATE"
    assert result[0]["spot_ticker"] == "STRONG"
    assert result[0]["relative_strength"] == 1.1


def test_weak_on_up_market_is_short(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("STRONG", 1.8, 2_000_000), _row("WEAK", -0.4, 1_900_000)], 0.7)
    result = scanner.scan(limit=2)
    assert any(x["selection_role"] == "SHORT_CANDIDATE" and x["spot_ticker"] == "WEAK" for x in result)


def test_strong_on_down_market_is_long(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("STRONG", 0.4, 2_000_000), _row("WEAK", -2.2, 1_900_000)], -0.6)
    result = scanner.scan(limit=2)
    assert result[0]["selection_role"] == "LONG_CANDIDATE"
    assert result[0]["relative_strength"] == 1.0


def test_weak_on_down_market_is_short(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("STRONG", -0.1, 2_000_000), _row("WEAK", -2.2, 1_900_000)], -0.6)
    result = scanner.scan(limit=2)
    assert any(x["selection_role"] == "SHORT_CANDIDATE" and x["spot_ticker"] == "WEAK" for x in result)


def test_tiny_relative_strength_is_not_directional(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("A", 0.23, 3_000_000), _row("B", 0.17, 3_000_000)], 0.20)
    assert scanner.scan(limit=3) == []


def test_d1_confirmation_overrides_intraday_direction(monkeypatch):
    rows = [_row("A", 1.5, 3_000_000), _row("B", -1.5, 2_000_000)]
    scanner = _scanner(monkeypatch, rows, 0.0)
    monkeypatch.setattr(scanner, "_daily_profile", lambda item, *args: _qualified_profile("SHORT" if item["spot_ticker"] == "A" else "LONG"))
    assert scanner.scan(limit=3) == []


def test_d1_benchmark_unavailable_blocks_direction(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("A", 2.0, 2_000_000), _row("B", -2.0, 1_900_000)], 0.0)
    monkeypatch.setattr(scanner, "_benchmark_daily", lambda *args: [])
    assert scanner.scan(limit=3) == []
    assert scanner._last_scan_diagnostics["daily_benchmark_available"] is False


def test_weekend_scan_uses_dswd_start(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)], 0.2, session=FakeWeekendSession())
    result = scanner.scan(limit=2)
    assert result
    assert scanner._last_scan_diagnostics["scan_window"] == "09:50-до закрытия MSK"
    assert scanner._last_scan_diagnostics["session"] == "WEEKEND_SESSION"


def test_scanner_continues_after_preferred_window(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)], 0.2, session=FakeAfternoonSession())
    assert scanner.scan(limit=2)
    assert scanner._last_scan_diagnostics["preferred_window_active"] is False
    assert scanner._last_scan_diagnostics["scan_window"] == "10:00-до закрытия MSK"


def test_coverage_gate_suppresses_partial_market(monkeypatch):
    rows = [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000), _row("C", 0.8, 1_800_000)]
    scanner = _scanner(monkeypatch, rows, 0.2)
    monkeypatch.setattr(scanner, "_analyze_one", lambda item, *args: None if item["spot_ticker"] == "C" else dict(item))
    assert scanner.scan(limit=2) == []
    assert scanner._last_scan_diagnostics["status"] == "INSUFFICIENT_COVERAGE"
    assert scanner._last_scan_diagnostics["coverage_percent"] == round(2 / 3 * 100, 1)


def test_rs_magnitude_participates_in_ranking(monkeypatch):
    rows = [_row("HIGH_RS", 1.0, 1_600_000), _row("HIGH_ATTENTION", 0.2, 3_000_000), _row("WEAK", -0.8, 1_500_000)]
    scanner = _scanner(monkeypatch, rows, 0.0)
    result = scanner.scan(limit=3)
    assert result[0]["spot_ticker"] == "HIGH_RS"
    assert result[0]["directional_score"] > result[1]["directional_score"]


def test_acceleration_requires_two_complete_windows():
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=FakeSession(), history_service=object())
    candles = [{"time": f"2026-09-02T07:{m:02d}:00Z", "close": 100.0, "money_volume": 100.0} for m in (0, 5, 10)]
    class History:
        def load(self, *args, **kwargs): return candles
    scanner.history = History()
    row = scanner._analyze_one({"spot_ticker": "TEST", "spot_class_code": "TQBR"}, FakeSession().get_trading_day(), time(7, 0), FakeSession().now())
    assert row["money_acceleration"] == 0.0


def test_acceleration_uses_equal_windows():
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=FakeSession(), history_service=object())
    candles = [{"time": f"2026-09-02T07:{m:02d}:00Z", "close": 100.0, "money_volume": money}
               for m, money in ((0, 100), (5, 100), (10, 100), (15, 200), (20, 200), (25, 200))]
    class History:
        def load(self, *args, **kwargs): return candles
    scanner.history = History()
    row = scanner._analyze_one({"spot_ticker": "TEST", "spot_class_code": "TQBR"}, FakeSession().get_trading_day(), time(7, 0), datetime(2026, 9, 2, 7, 30, tzinfo=FakeSession.TIMEZONE))
    assert round(row["money_acceleration"], 1) == 100.0
