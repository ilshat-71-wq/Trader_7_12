from api.bcs_api import BCSAPI
from api.request_helper import RequestHelper


def test_transient_authorization_post_failure_does_not_crash_startup(monkeypatch):
    api = BCSAPI()
    monkeypatch.setattr(api, "access_token", None)
    monkeypatch.setattr(api, "_access_token_expires_at", 0.0)
    monkeypatch.setattr("api.bcs_api.get_refresh_token", lambda: "test-refresh-token")

    calls = []

    def fail_post(cls, url, headers=None, json=None, data=None, timeout=None, max_retries=None):
        calls.append(url)
        raise RuntimeError("simulated BCS read timeout")

    monkeypatch.setattr(RequestHelper, "post", classmethod(fail_post))

    assert api.authorize(force=True) is False
    assert api.access_token is None
    # Repeated constructors must not block startup with another 8-second POST.
    assert api.authorize() is False
    assert len(calls) == 1
