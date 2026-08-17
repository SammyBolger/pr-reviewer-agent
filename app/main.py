import hashlib
import hmac
import logging

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.config import settings
from app.github.auth import installation_token
from app.review.runner import run_review

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("pr-reviewer")

app = FastAPI(title="pr-reviewer-agent")

REVIEW_ACTIONS = {"opened", "synchronize", "reopened"}
SLASH_COMMANDS = ("/review-again", "/review")


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

    elif event == "issue_comment" and payload.get("action") == "created":
        if _is_slash_command(payload):
            background.add_task(_run_slash_command, payload)

    return {"received": True}


def _is_slash_command(payload: dict) -> bool:
    issue = payload.get("issue") or {}
    if "pull_request" not in issue:
        return False
    body = (payload.get("comment") or {}).get("body", "").strip().lower()
    return body.startswith(SLASH_COMMANDS)


async def _run_slash_command(payload: dict) -> None:
    try:
        repo = payload["repository"]["full_name"]
        pr_number = payload["issue"]["number"]
        installation_id = payload["installation"]["id"]

        log.info("slash command '/review-again' received for %s#%s", repo, pr_number)

        token = await installation_token(installation_id)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
                headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            )
            r.raise_for_status()
            pr = r.json()

        synthetic = {
            "pull_request": pr,
            "repository": payload["repository"],
            "installation": payload["installation"],
        }
        await run_review(synthetic)
    except Exception:
        log.exception("slash command review failed")


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
