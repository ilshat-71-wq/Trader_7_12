from services.open_interest_service import OpenInterestService


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"futoi": {"columns": ["ticker", "pos_long"], "data": [["Si", 123.0]]}}


def test_open_interest_default_http_uses_request_helper(monkeypatch):
    calls = []

    def fake_get(url, headers=None, timeout=None, **kwargs):
        calls.append({"url": url, "headers": headers, "timeout": timeout, "kwargs": kwargs})
        return _Response()

    monkeypatch.setattr("services.open_interest_service.RequestHelper.get", fake_get)

    service = OpenInterestService()
    payload = service._default_get("https://iss.moex.com/test", timeout=7)

    assert payload["futoi"]["data"][0][0] == "Si"
    assert len(calls) == 1
    assert calls[0]["url"] == "https://iss.moex.com/test"
    assert calls[0]["headers"]["User-Agent"].startswith("Trader_7_12/")
    assert calls[0]["timeout"] == 7


def test_open_interest_http_error_is_propagated(monkeypatch):
    class ErrorResponse:
        status_code = 500

        def raise_for_status(self):
            raise RuntimeError("HTTP 500")

    monkeypatch.setattr(
        "services.open_interest_service.RequestHelper.get",
        lambda *args, **kwargs: ErrorResponse(),
    )

    service = OpenInterestService()

    try:
        service._default_get("https://iss.moex.com/test", timeout=7)
    except RuntimeError as exc:
        assert str(exc) == "HTTP 500"
    else:
        raise AssertionError("HTTP error was not propagated")
