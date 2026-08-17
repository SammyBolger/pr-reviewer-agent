from fastapi.testclient import TestClient


def _client(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", "test-secret")
    return TestClient(main_mod.app)


def test_root_returns_200_and_metadata(monkeypatch):
    with _client(monkeypatch) as c:
        r = c.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["app"] == "pr-reviewer-agent"
    assert "endpoints" in body
    assert "webhook" in body["endpoints"]


def test_root_does_not_leak_secrets(monkeypatch):
    with _client(monkeypatch) as c:
        r = c.get("/")
    body_str = r.text.lower()
    for forbidden in ("secret", "token", "api_key", "private_key", "sk-ant"):
        assert forbidden not in body_str, f"root response leaks {forbidden!r}"
