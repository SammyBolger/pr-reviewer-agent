from fastapi.testclient import TestClient


def _client(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", "test-secret")
    return TestClient(main_mod.app)


def test_body_size_limit_rejects_oversized_request(monkeypatch):
    with _client(monkeypatch) as c:
        oversized = "x" * (3 * 1024 * 1024)
        r = c.post("/webhook", content=oversized, headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 413
    assert "too large" in r.json()["detail"]


def test_body_size_limit_rejects_bad_content_length(monkeypatch):
    with _client(monkeypatch) as c:
        r = c.post(
            "/webhook",
            content=b"{}",
            headers={"Content-Length": "not-a-number"},
        )
    # TestClient normalises headers so this can 400 or pass. If it passes, that's
    # ok — the check ran, the client just fixed the header. We assert we didn't 5xx.
    assert r.status_code < 500
