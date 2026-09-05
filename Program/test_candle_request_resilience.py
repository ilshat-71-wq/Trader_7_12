"""Offline regression tests for resilient BCS candle reads."""

from datetime import datetime, timezone

from api.bcs_api import BCSAPI
from api.request_helper import RequestHelper


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"bars": [{"time": "2026-08-18T05:00:00Z", "close": 91.0}]}
        self.text = ""

    def json(self):
        return self._payload


def test_candle_cache_reuses_equivalent_requests():
    api = BCSAPI()
    calls = []
    original = RequestHelper.get

    def fake_get(*args, **kwargs):
        calls.append(kwargs)
        return FakeResponse()

    RequestHelper.get = staticmethod(fake_get)
    try:
        start = datetime(2026, 8, 18, 5, 0, 12, tzinfo=timezone.utc)
        end = datetime(2026, 8, 18, 5, 12, 44, tzinfo=timezone.utc)
        first = api.get_candles("BRENT1026", "SPBFUT", "H1", start, end)
        second = api.get_candles("BRENT1026", "SPBFUT", "H1", start, end)
        assert first == second
        assert len(calls) == 1
        assert calls[0]["timeout"] == api.CANDLE_TIMEOUT
        assert calls[0]["max_retries"] == api.CANDLE_RETRIES
    finally:
        RequestHelper.get = staticmethod(original)


def test_candle_request_uses_bounded_retry_profile():
    api = BCSAPI()
    captured = {}
    original = RequestHelper.get

    def fake_get(*args, **kwargs):
        captured.update(kwargs)
        return FakeResponse()

    RequestHelper.get = staticmethod(fake_get)
    try:
        api.get_candles("BRENT1026", "SPBFUT", "H1")
        assert captured["timeout"] == api.CANDLE_TIMEOUT
        assert captured["max_retries"] == api.CANDLE_RETRIES
    finally:
        RequestHelper.get = staticmethod(original)


if __name__ == "__main__":
    test_candle_cache_reuses_equivalent_requests()
    print("PASS test_candle_cache_reuses_equivalent_requests")
    test_candle_request_uses_bounded_retry_profile()
    print("PASS test_candle_request_uses_bounded_retry_profile")
    print("ALL TESTS PASSED")
