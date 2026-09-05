from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_attention_scanner_service import MarketAttentionScannerService
from services.spot_universe_service import SpotUniverseService


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

    def get_session_start(self, value=None):
        return self.MORNING_START

    def is_market_open(self, value=None):
        return True


class FakeWeekendSession(FakeSession):
    WEEKEND_START = datetime(2026, 9, 5, 9, 50, tzinfo=FakeSession.TIMEZONE).time()

    def now(self):
        return datetime(2026, 9, 5, 10, 44, tzinfo=self.TIMEZONE)

    def get_session(self):
        return "WEEKEND_SESSION"

    def get_session_info(self):
        return {"session": "WEEKEND_SESSION"}

    def get_session_start(self, value=None):
        return self.WEEKEND_START


class FakeAfternoonSession(FakeSession):
    def now(self):
        return datetime(2026, 9, 2, 14, 0, tzinfo=self.TIMEZONE)

    def get_session(self):
        return "MAIN"

    def get_session_info(self):
        return {"session": "MAIN"}

    def get_session_start(self, value=None):
        return self.MAIN_START


def _scanner(monkeypatch, rows, benchmark=0.0, session=None):
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=session or FakeSession(), history_service=object())
    monkeypatch.setattr(scanner, "build_universe", lambda: [dict(x) for x in rows])
    monkeypatch.setattr(scanner, "_benchmark", lambda *args: ("IMOEX2", "INDICES", benchmark))
    monkeypatch.setattr(scanner, "_analyze_one", lambda item, *args: dict(item))
    return scanner


def _row(ticker, change, money, acceleration=0.0):
    return {"spot_ticker": ticker, "spot_class_code": "TQBR", "market_group": "STOCK", "change_percent": change,
            "session_money": money, "money_per_minute": money / 180.0, "recent_money": money / 3.0,
            "recent_money_per_minute": money / 45.0, "money_acceleration": acceleration, "data_status": "AVAILABLE"}


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


def test_tiny_relative_strength_is_not_directional(monkeypatch):
    rows = [
        _row("TINY_LONG", 0.23, 3_000_000),
        _row("TINY_SHORT", 0.17, 3_000_000),
    ]
    scanner = _scanner(monkeypatch, rows, 0.20)
    result = scanner.scan(limit=3)
    assert result == []
    assert scanner._last_scan_diagnostics["long_candidate"] is None
    assert scanner._last_scan_diagnostics["short_candidate"] is None


def test_relative_strength_magnitude_participates_in_directional_ranking(monkeypatch):
    rows = [
        _row("HIGH_RS", 1.00, 1_600_000),
        _row("HIGH_ATTENTION", 0.20, 3_000_000),
        _row("WEAK", -0.80, 1_500_000),
    ]
    scanner = _scanner(monkeypatch, rows, 0.0)
    result = scanner.scan(limit=3)
    assert result[0]["selection_role"] == "LONG_CANDIDATE"
    assert result[0]["spot_ticker"] == "HIGH_RS"
    assert result[0]["relative_strength_quality"] == "MEANINGFUL"
    assert result[0]["directional_score"] > result[1]["directional_score"]
    assert any(x["selection_role"] == "SHORT_CANDIDATE" and x["spot_ticker"] == "WEAK" for x in result)


def test_weekend_scan_uses_dswd_start(monkeypatch):
    captured = {}
    scanner = _scanner(monkeypatch, [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)], 0.2,
                       session=FakeWeekendSession())

    def analyze(item, trading_date, session_start, now):
        captured["session_start"] = session_start
        return dict(item)

    monkeypatch.setattr(scanner, "_analyze_one", analyze)
    result = scanner.scan(limit=2)
    assert result
    assert captured["session_start"].strftime("%H:%M") == "09:50"
    assert scanner._last_scan_diagnostics["session"] == "WEEKEND_SESSION"
    assert scanner._last_scan_diagnostics["scan_window"] == "09:50-до закрытия MSK"


def test_scanner_continues_after_preferred_window(monkeypatch):
    session = FakeAfternoonSession()
    scanner = _scanner(monkeypatch, [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)], 0.2, session=session)
    result = scanner.scan(limit=2)
    assert result
    assert scanner._last_scan_diagnostics["session"] == "MAIN"
    assert scanner._last_scan_diagnostics["scan_window"] == "10:00-до закрытия MSK"
    assert scanner._last_scan_diagnostics["preferred_window_active"] is False


def test_benchmark_uses_nested_bcs_class_code_and_m5(monkeypatch):
    class NestedMetadataAPI(FakeAPI):
        def get_instruments_by_tickers(self, tickers):
            return [{"ticker": "IMOEX2", "boards": [{"classCode": "INDX", "exchange": "MOEX"}], "subTitle": "IMOEX2"}]

        def get_instruments(self, instrument_type="FUTURES"):
            return []

    session = FakeSession()
    scanner = MarketAttentionScannerService(api=NestedMetadataAPI(), session_service=session, history_service=object())
    captured = {}

    def candles(ticker, code, start, end):
        captured["ticker"] = ticker
        captured["code"] = code
        return [{"time": "2026-09-02T07:00:00Z", "close": 100.0}, {"time": "2026-09-02T07:05:00Z", "close": 101.0}]

    monkeypatch.setattr(scanner, "_candles", candles)
    ticker, code, change = scanner._benchmark(session.get_trading_day(), session.now(), session.MORNING_START)
    assert ticker == "IMOEX2"
    assert code == "INDX"
    assert round(change, 4) == 1.0
    assert captured == {"ticker": "IMOEX2", "code": "INDX"}


def test_benchmark_uses_live_quote_when_m5_is_missing(monkeypatch):
    class QuoteAPI(FakeAPI):
        def get_instruments_by_tickers(self, tickers):
            return [{"ticker": "IMOEX2", "classCode": "SNDX"}]

        def get_instruments(self, instrument_type="FUTURES"):
            return []

        def get_quotes(self, instruments):
            return {"records": [{"ticker": "IMOEX2", "classCode": "SNDX", "open": 100.0, "last": 101.5,
                                  "dateTime": "2026-09-02T07:00:00.000Z"}]}

    session = FakeSession()
    scanner = MarketAttentionScannerService(api=QuoteAPI(), session_service=session, history_service=object())
    monkeypatch.setattr(scanner, "_candles", lambda *args: [])
    ticker, code, change = scanner._benchmark(session.get_trading_day(), session.now(), session.MORNING_START)
    assert ticker == "IMOEX2"
    assert code == "SNDX"
    assert round(change, 4) == 1.5


def test_stale_benchmark_quote_is_rejected(monkeypatch):
    class StaleQuoteAPI(FakeAPI):
        def get_instruments_by_tickers(self, tickers):
            return [{"ticker": "IMOEX2", "classCode": "SNDX"}]

        def get_instruments(self, instrument_type="FUTURES"):
            return []

        def get_quotes(self, instruments):
            return {"records": [{"ticker": "IMOEX2", "classCode": "SNDX", "open": 100.0, "last": 101.5,
                                  "dateTime": "2026-09-02T06:00:00.000Z"}]}

    session = FakeSession()
    scanner = MarketAttentionScannerService(api=StaleQuoteAPI(), session_service=session, history_service=object())
    monkeypatch.setattr(scanner, "_candles", lambda *args: [])
    assert scanner._benchmark(session.get_trading_day(), session.now(), session.MORNING_START) == (None, None, None)


def test_weekend_universe_respects_moex_weekend_session_flag():
    class WeekendMetadataAPI(FakeAPI):
        def get_instruments(self, instrument_type="FUTURES"):
            if instrument_type != "STOCK":
                return []
            return [
                {"ticker": "WEEKEND_Y", "boards": [{"classCode": "TQBR", "exchange": "MOEX"}], "WEEKENDSESSION": "Y"},
                {"ticker": "WEEKEND_N", "boards": [{"classCode": "TQBR", "exchange": "MOEX"}], "WEEKENDSESSION": "N"},
            ]

    universe = SpotUniverseService(api=WeekendMetadataAPI()).load(weekend_session=True)
    tickers = {row["spot_ticker"] for row in universe}
    assert "WEEKEND_Y" in tickers
    assert "WEEKEND_N" not in tickers


def test_directional_candidates_are_suppressed_when_coverage_is_insufficient(monkeypatch):
    rows = [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000), _row("C", 0.8, 1_800_000)]
    scanner = _scanner(monkeypatch, rows, 0.2)
    original = scanner._analyze_one

    def partial(item, *args):
        if item["spot_ticker"] == "C":
            return None
        return original(item, *args)

    monkeypatch.setattr(scanner, "_analyze_one", partial)
    scanner.MIN_DIRECTIONAL_COVERAGE = 0.80
    result = scanner.scan(limit=2)
    assert result == []
    assert scanner._last_scan_diagnostics["status"] == "INSUFFICIENT_COVERAGE"
    assert scanner._last_scan_diagnostics["coverage_ok"] is False
    assert scanner._last_scan_diagnostics["skip_reasons"]["INSUFFICIENT_M5"] == 1


def test_coverage_diagnostics_report_partial_scan(monkeypatch):
    rows = [_row("A", 1.0, 2_000_000), _row("B", -1.0, 1_900_000)]
    scanner = _scanner(monkeypatch, rows, 0.2)
    original = scanner._analyze_one

    def partial(item, *args):
        if item["spot_ticker"] == "B":
            return None
        return original(item, *args)

    monkeypatch.setattr(scanner, "_analyze_one", partial)
    scanner.MIN_DIRECTIONAL_COVERAGE = 0.40
    result = scanner.scan(limit=2)
    assert result
    assert scanner._last_scan_diagnostics["coverage_percent"] == 50.0
    assert scanner._last_scan_diagnostics["skipped_total"] == 1
    assert scanner._last_scan_diagnostics["skip_samples"]["INSUFFICIENT_M5"] == ["B"]


def test_acceleration_score_is_relative_and_bounded(monkeypatch):
    rows = [
        _row("LOW", 0.2, 2_000_000, acceleration=-80.0),
        _row("MID", 0.3, 2_000_000, acceleration=5.0),
        _row("HIGH", 0.4, 2_000_000, acceleration=50.8),
        _row("EXTREME", 0.5, 2_000_000, acceleration=5000.0),
    ]
    scanner = _scanner(monkeypatch, rows, 0.0)
    result = scanner.scan(limit=4)
    by_ticker = {row["spot_ticker"]: row for row in result}
    assert by_ticker["LOW"]["attention_score"] < by_ticker["HIGH"]["attention_score"]
    assert by_ticker["HIGH"]["attention_score"] < by_ticker["EXTREME"]["attention_score"]
    assert all(0.0 <= row["attention_score"] <= 100.0 for row in result)


def test_flow_acceleration_requires_two_complete_15_minute_windows():
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=FakeSession(), history_service=object())
    candles = [
        {"time": "2026-09-02T07:00:00Z", "close": 100.0, "money_volume": 100.0},
        {"time": "2026-09-02T07:05:00Z", "close": 100.0, "money_volume": 100.0},
        {"time": "2026-09-02T07:10:00Z", "close": 100.0, "money_volume": 100.0},
        {"time": "2026-09-02T07:15:00Z", "close": 100.0, "money_volume": 200.0},
        {"time": "2026-09-02T07:20:00Z", "close": 100.0, "money_volume": 200.0},
        {"time": "2026-09-02T07:25:00Z", "close": 100.0, "money_volume": 200.0},
    ]

    class History:
        def load(self, *args, **kwargs):
            return candles[:3]

    scanner.history = History()
    item = {"spot_ticker": "TEST", "spot_class_code": "TQBR"}
    row = scanner._analyze_one(item, datetime(2026, 9, 2).date(), FakeSession.MORNING_START,
                               datetime(2026, 9, 2, 7, 12, tzinfo=FakeSession.TIMEZONE))
    assert row["money_acceleration"] == 0.0


def test_flow_acceleration_uses_equal_15_minute_windows():
    scanner = MarketAttentionScannerService(api=FakeAPI(), session_service=FakeSession(), history_service=object())
    candles = [
        {"time": f"2026-09-02T07:{minute:02d}:00Z", "close": 100.0, "money_volume": money}
        for minute, money in [(0, 100.0), (5, 100.0), (10, 100.0), (15, 200.0), (20, 200.0), (25, 200.0)]
    ]

    class History:
        def load(self, *args, **kwargs):
            return candles

    scanner.history = History()
    item = {"spot_ticker": "TEST", "spot_class_code": "TQBR"}
    row = scanner._analyze_one(item, datetime(2026, 9, 2).date(), FakeSession.MORNING_START,
                               datetime(2026, 9, 2, 7, 30, tzinfo=FakeSession.TIMEZONE))
    assert round(row["money_acceleration"], 1) == 100.0
