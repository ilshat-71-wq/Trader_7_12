import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Program"))

from api.bcs_api import BCSAPI


class FakeResponse:
    def __init__(self, status_code, records):
        self.status_code = status_code
        self._records = records

    def json(self):
        return {"records": self._records}


def _records(start, count):
    return [
        {
            "ticker": f"TEST{index}",
            "classCode": "TEST",
        }
        for index in range(start, start + count)
    ]


def test_get_instruments_handles_bcs_200_record_pages(monkeypatch):
    api = BCSAPI()
    api._instrument_metadata_cache.clear()

    calls = []

    def fake_get(url, **kwargs):
        page = kwargs["params"]["page"]
        calls.append(page)
        if page == 0:
            return FakeResponse(200, _records(0, 200))
        if page == 1:
            return FakeResponse(200, _records(200, 200))
        return FakeResponse(200, [])

    monkeypatch.setattr("api.bcs_api.RequestHelper.get", fake_get)

    records = api.get_instruments("STOCK")

    assert len(records) == 400
    assert calls == [0, 1, 2]


def test_get_instruments_cache_avoids_reloading_metadata(monkeypatch):
    api = BCSAPI()
    api._instrument_metadata_cache.clear()

    calls = []

    def fake_get(url, **kwargs):
        page = kwargs["params"]["page"]
        calls.append(page)
        if page == 0:
            return FakeResponse(200, _records(0, 1))
        return FakeResponse(200, [])

    monkeypatch.setattr("api.bcs_api.RequestHelper.get", fake_get)

    first = api.get_instruments("CURRENCY")
    second = api.get_instruments("CURRENCY")

    assert len(first) == 1
    assert len(second) == 1
    assert calls == [0]


def test_get_instruments_continues_when_server_returns_100_for_200_request(monkeypatch):
    api = BCSAPI()
    api._instrument_metadata_cache.clear()

    calls = []

    def fake_get(url, **kwargs):
        page = kwargs["params"]["page"]
        calls.append(page)
        if page == 0:
            return FakeResponse(200, _records(0, 100))
        if page == 1:
            return FakeResponse(200, _records(100, 100))
        return FakeResponse(200, [])

    monkeypatch.setattr("api.bcs_api.RequestHelper.get", fake_get)

    records = api.get_instruments("FUTURES")

    assert len(records) == 200
    assert calls == [0, 1, 2]
