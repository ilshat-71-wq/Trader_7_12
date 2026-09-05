from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_attention_scanner_service import MarketAttentionScannerService


class FakeAPI:
    access_token = "ok"
    def authorize(self):
        return True


class FakeSession:
    TIMEZONE = ZoneInfo("Europe/Moscow")
    MORNING_START = datetime(2026, 9, 2, 7, 0, tzinfo=TIMEZONE).time()
    MAIN_START = datetime(2026, 9, 2, 10, 0, tzinfo=TIMEZONE).time()
    def now(self):
        return datetime(2026, 9, 2, 10, 0, tzinfo=self.TIMEZONE)
    def get_trading_day(self):
        return self.now().date()
    def get_session(self):
        return "MORNING"
    def get_session_info(self):
        return {"session": "MORNING"}
    def get_window(self):
        return (self.MORNING_START, self.MAIN_START)
    def is_market_open(self, value=None):
        return True


class FakeWeekendSession(FakeSession):
    def now(self):
        return datetime(2026, 9, 5, 10, 44, tzinfo=self.TIMEZONE)
    def get_session(self):
        return "WEEKEND_SESSION"
    def get_session_info(self):
        return {"session": "WEEKEND_SESSION"}


def _scanner(monkeypatch, rows, benchmark=0.0, session=None):
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=session or FakeSession(), history_service=object())
    monkeypatch.setattr(scanner, "build_universe", lambda: [dict(x) for x in rows])
    monkeypatch.setattr(scanner, "_benchmark", lambda *args: ("IMOEX2", "INDICES", benchmark))
    monkeypatch.setattr(scanner, "_analyze_one", lambda item, *args: dict(item))
    return scanner


def _row(ticker, change, money):
    return {"spot_ticker": ticker, "spot_class_code": "TQBR", "market_group": "STOCK", "change_percent": change,
            "session_money": money, "money_per_minute": money / 180.0, "recent_money": money / 3.0,
            "recent_money_per_minute": money / 45.0, "money_acceleration": 0.0, "data_status": "AVAILABLE"}


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


def test_no_benchmark_means_no_directional_selection(monkeypatch):
    scanner = _scanner(monkeypatch, [_row("A", 2.0, 2_000_000), _row("B", -2.0, 1_900_000)], None)
    result = scanner.scan(limit=3)
    assert result == []
    assert scanner._last_scan_diagnostics["benchmark"] is None


def test_weekend_scan_uses_dswd_start(monkeypatch):
    captured = {}
    scanner = _scanner(
        monkeypatch,
        [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)],
        0.2,
        session=FakeWeekendSession(),
    )

    def analyze(item, trading_date, session_start, now):
        captured["session_start"] = session_start
        return dict(item)

    monkeypatch.setattr(scanner, "_analyze_one", analyze)
    result = scanner.scan(limit=2)
    assert result
    assert captured["session_start"].strftime("%H:%M") == "09:50"
    assert scanner._last_scan_diagnostics["session"] == "WEEKEND_SESSION"
    assert scanner._last_scan_diagnostics["scan_window"] == "09:50-13:00 MSK"
