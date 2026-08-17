import pytest
from fastapi.testclient import TestClient

from app.middleware import BodySizeLimitMiddleware


def _client(monkeypatch):
    from app import main as main_mod
    monkeypatch.setattr(main_mod.settings, "github_webhook_secret", "test-secret")
    return TestClient(main_mod.app)


# ---------- integration-through-testclient tests ----------

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
    assert r.status_code == 401  # no signature; middleware let it through


# ---------- raw ASGI tests, no TestClient normalisation ----------

async def _crash_app(scope, receive, send):
    # If the middleware ever forwards an oversized body to us, this will run
    # and fail the test loudly.
    raise AssertionError("middleware forwarded oversized body to the app")


async def _collect(sent: list):
    async def send(message):
        sent.append(message)
    return send


def _scope_with_content_length(n: int) -> dict:
    return {
        "type": "http",
        "method": "POST",
        "path": "/webhook",
        "headers": [
            (b"content-length", str(n).encode()),
            (b"content-type", b"application/octet-stream"),
        ],
    }


def _scope_chunked() -> dict:
    return {
        "type": "http",
        "method": "POST",
        "path": "/webhook",
        "headers": [
            (b"transfer-encoding", b"chunked"),
            (b"content-type", b"application/octet-stream"),
        ],
    }


@pytest.mark.asyncio
async def test_asgi_middleware_rejects_oversized_content_length_without_calling_app():
    mw = BodySizeLimitMiddleware(app=_crash_app, max_bytes=1024)
    sent: list = []
    send = await _collect(sent)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    await mw(_scope_with_content_length(2048), receive, send)

    statuses = [m for m in sent if m["type"] == "http.response.start"]
    assert statuses and statuses[0]["status"] == 413


@pytest.mark.asyncio
async def test_asgi_middleware_stops_chunked_uploads_over_limit_without_calling_app():
    mw = BodySizeLimitMiddleware(app=_crash_app, max_bytes=1024)
    sent: list = []
    send = await _collect(sent)

    delivered = 0
    total_chunks = 5

    async def receive():
        nonlocal delivered
        if delivered >= total_chunks:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered += 1
        return {
            "type": "http.request",
            "body": b"x" * 512,
            "more_body": delivered < total_chunks,
        }

    await mw(_scope_chunked(), receive, send)

    statuses = [m for m in sent if m["type"] == "http.response.start"]
    assert statuses and statuses[0]["status"] == 413


@pytest.mark.asyncio
async def test_asgi_middleware_forwards_valid_body_to_app():
    seen_bodies: list[bytes] = []

    async def echo_app(scope, receive, send):
        # Read the full body via the (potentially replayed) receive callable
        chunks = []
        more = True
        while more:
            m = await receive()
            if m["type"] != "http.request":
                break
            chunks.append(m.get("body", b""))
            more = m.get("more_body", False)
        seen_bodies.append(b"".join(chunks))
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    mw = BodySizeLimitMiddleware(app=echo_app, max_bytes=1024)
    sent: list = []
    send = await _collect(sent)

    payload = b'{"payload":"small"}'

    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": payload, "more_body": False}

    await mw(_scope_with_content_length(len(payload)), receive, send)

    statuses = [m for m in sent if m["type"] == "http.response.start"]
    assert statuses and statuses[0]["status"] == 200
    assert seen_bodies == [payload]
