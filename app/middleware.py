from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """
    Reject requests whose body exceeds max_bytes.

    We check Content-Length up front and, for requests without a trustworthy
    Content-Length (e.g. chunked uploads), buffer the body in the middleware
    up to max_bytes+1 before dispatching. That way the wrapped app never sees
    an oversized payload and we always send our own 413 cleanly.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = 2 * 1024 * 1024) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await self._reject(send, f"request body too large (>{self.max_bytes} bytes)")
                    return
            except ValueError:
                await self._reject(send, "invalid content-length header", status=400)
                return

        buffered = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                # http.disconnect or similar; propagate to app
                await self.app(scope, self._replay(buffered), send)
                return
            chunk = message.get("body", b"") or b""
            buffered += chunk
            more_body = message.get("more_body", False)
            if len(buffered) > self.max_bytes:
                await self._reject(send, f"request body too large (>{self.max_bytes} bytes)")
                return

        await self.app(scope, self._replay(buffered), send)

    def _replay(self, body: bytes) -> Receive:
        sent = False

        async def receive() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        return receive

    async def _reject(self, send: Send, detail: str, status: int = 413) -> None:
        response = JSONResponse({"detail": detail}, status_code=status)
        await response({"type": "http", "method": "POST", "headers": []}, self._noop_receive, send)

    @staticmethod
    async def _noop_receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}
