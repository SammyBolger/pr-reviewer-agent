import hashlib
import hmac
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select

from app.config import settings
from app.db.models import ReviewRecord
from app.db.session import SessionLocal, init_db
from app.github.auth import installation_token
from app.middleware import BodySizeLimitMiddleware
from app.review.runner import run_review

logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("pr-reviewer")

REVIEW_ACTIONS = {"opened", "synchronize", "reopened"}
SLASH_COMMANDS = ("/review-again", "/review")

# 2 MB is more than enough for any GitHub webhook payload we care about.
MAX_REQUEST_BYTES = 2 * 1024 * 1024

# Default limit is intentionally tight. Endpoints that need more (like /webhook)
# override with their own decorator. This keeps unauthenticated endpoints
# defensively rate-limited even in the event of misconfiguration.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception:
        log.exception("db init failed, continuing without persistence")
    if not settings.dashboard_token:
        log.warning(
            "DASHBOARD_TOKEN is unset. /dashboard will return 404 to every request. "
            "Set DASHBOARD_TOKEN to a long random string to enable it."
        )
    yield


app = FastAPI(title="pr-reviewer-agent", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_REQUEST_BYTES)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/dashboard")
@limiter.limit("30/minute")
async def dashboard(request: Request):
    _require_dashboard_auth(request)
    async with SessionLocal() as session:
        stats = await session.execute(
            select(
                func.count(ReviewRecord.id),
                func.sum(ReviewRecord.tokens_in),
                func.sum(ReviewRecord.tokens_out),
                func.sum(ReviewRecord.cost_usd),
                func.avg(ReviewRecord.confidence),
            )
        )
        total, ti, to, cost, avg_conf = stats.one()

        recent = await session.execute(
            select(ReviewRecord).order_by(desc(ReviewRecord.created_at)).limit(20)
        )
        rows = recent.scalars().all()

    return {
        "totals": {
            "reviews": total or 0,
            "tokens_in": ti or 0,
            "tokens_out": to or 0,
            "cost_usd": round(cost or 0.0, 4),
            "avg_confidence": round(avg_conf or 0.0, 2),
        },
        "recent": [
            {
                "repo": r.repo,
                "pr": r.pr_number,
                "model": r.model,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "cost_usd": round(r.cost_usd, 4),
                "confidence": round(r.confidence, 2),
                "num_concerns": r.num_concerns,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@app.post("/webhook")
@limiter.limit("300/minute")
async def webhook(request: Request, background: BackgroundTasks):
    body = await request.body()

    # Defense in depth: the BodySizeLimitMiddleware already enforces this, but
    # if the middleware is ever removed or a bug lets a huge body through, we
    # still refuse to process it here.
    if len(body) > MAX_REQUEST_BYTES:
        raise HTTPException(status_code=413, detail="request body too large")

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="bad signature")

    event = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event == "pull_request" and payload.get("action") in REVIEW_ACTIONS:
        background.add_task(_safe_run_review, payload)
    elif (
        event == "issue_comment"
        and payload.get("action") == "created"
        and _is_slash_command(payload)
    ):
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


def _require_dashboard_auth(request: Request) -> None:
    expected = settings.dashboard_token
    if not expected:
        # Explicitly refuse to serve the dashboard when no token is configured.
        # Set DASHBOARD_TOKEN in production to enable it.
        raise HTTPException(status_code=404, detail="not found")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    presented = header[len("Bearer "):]
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


def verify_signature(body: bytes, signature_header: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
