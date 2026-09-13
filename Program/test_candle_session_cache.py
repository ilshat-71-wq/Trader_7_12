from datetime import datetime, timezone

from api.bcs_api import BCSAPI


class FakeResponse:
    status_code = 200

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def _api(monkeypatch):
    api = BCSAPI.__new__(BCSAPI)
    api.market_url = "https://example.test"
    api.CANDLE_CACHE_TTL = 30.0
    api.CANDLE_TIMEOUT = 5
    api.CANDLE_RETRIES = 0
    api._candle_cache = {}
    api._candle_semaphore = __import__("threading").Semaphore(4)
    api.headers = lambda: {}

    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs["params"])
        return FakeResponse({
            "records": [
                {"dateTime": "2026-09-10T07:00:00Z", "close": 100},
                {"dateTime": "2026-09-10T10:00:00Z", "close": 101},
                {"dateTime": "2026-09-10T12:00:00Z", "close": 102},
                {"dateTime": "2026-09-10T16:00:00Z", "close": 103},
                {"dateTime": "2026-09-10T23:59:00Z", "close": 104},
            ]
        })

    monkeypatch.setattr("api.bcs_api.RequestHelper.get", fake_get)
    return api, calls


def test_m5_overlapping_requests_share_one_session_window(monkeypatch):
    api, calls = _api(monkeypatch)

    first = api.get_candles(
        "SBER",
        "TQBR",
        "M5",
        datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc),
    )
    second = api.get_candles(
        "SBER",
        "TQBR",
        "M5",
        datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc),
    )

    assert len(calls) == 1
    assert calls[0]["startDate"] == "2026-09-10T04:00:00.000Z"
    assert calls[0]["endDate"] == "2026-09-10T20:59:59.000Z"

    assert [r["close"] for r in first["records"]] == [101, 102]
    assert [r["close"] for r in second["records"]] == [102, 103]


def test_m5_different_day_does_not_share_cache(monkeypatch):
    api, calls = _api(monkeypatch)

    api.get_candles(
        "SBER",
        "TQBR",
        "M5",
        datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 10, 13, 0, tzinfo=timezone.utc),
    )
    api.get_candles(
        "SBER",
        "TQBR",
        "M5",
        datetime(2026, 9, 11, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 11, 13, 0, tzinfo=timezone.utc),
    )

    assert len(calls) == 2


def test_non_m5_keeps_exact_window_cache(monkeypatch):
    api, calls = _api(monkeypatch)

    start = datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc)

    api.get_candles("SBER", "TQBR", "H1", start, end)
    api.get_candles("SBER", "TQBR", "H1", start, end)

    assert len(calls) == 1
    assert calls[0]["startDate"] == "2026-09-10T09:00:00.000Z"
    assert calls[0]["endDate"] == "2026-09-10T10:00:00.000Z"
