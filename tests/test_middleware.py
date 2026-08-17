from fastapi.testclient import TestClient


def _client(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", "test-secret")
    return TestClient(main_mod.app)


def test_body_size_limit_rejects_oversized_content_length(monkeypatch):
    with _client(monkeypatch) as c:
        oversized = "x" * (3 * 1024 * 1024)
        r = c.post("/webhook", content=oversized, headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 413
    assert "too large" in r.json()["detail"]


def test_body_size_limit_rejects_streamed_oversized_body(monkeypatch):
    def big_stream():
        for _ in range(4):
            yield b"x" * (1024 * 1024)

    with _client(monkeypatch) as c:
        r = c.post(
            "/webhook",
            content=big_stream(),
            headers={"Content-Type": "application/octet-stream", "Transfer-Encoding": "chunked"},
        )
    assert r.status_code == 413


def test_body_size_limit_accepts_normal_payload(monkeypatch):
    with _client(monkeypatch) as c:
        r = c.post(
            "/webhook",
            content=b'{"payload": "ok"}',
            headers={"Content-Type": "application/json"},
        )
    # No signature -> 401. Point is: not blocked by size middleware.
    assert r.status_code == 401
