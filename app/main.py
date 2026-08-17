import asyncio
import hashlib
import hmac
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.config import settings
from app.review.runner import run_review

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("pr-reviewer")

app = FastAPI(title="pr-reviewer-agent")

REVIEW_ACTIONS = {"opened", "synchronize", "reopened"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="bad signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "pull_request" and payload.get("action") in REVIEW_ACTIONS:
        background.add_task(_safe_run_review, payload)

    return {"received": True}


async def _safe_run_review(payload: dict) -> None:
    try:
        await run_review(payload)
    except Exception:
        log.exception("review failed")


def verify_signature(body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
