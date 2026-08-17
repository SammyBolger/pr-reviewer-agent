import time

import httpx
import jwt

from app.config import settings


def app_jwt() -> str:
    now = int(time.time())
    key = _load_private_key()
    payload = {
        "iat": now - 60,
        "exp": now + 9 * 60,
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, key, algorithm="RS256")


def _load_private_key() -> str:
    # In production the PEM is loaded from a secret env var (Fly, Render, etc.).
    # In local dev it's a file on disk. Env var wins if both are set.
    if settings.github_app_private_key.strip():
        return settings.github_app_private_key
    return settings.github_app_private_key_path.read_text()


async def installation_token(installation_id: int) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt()}",
                "Accept": "application/vnd.github+json",
            },
        )
        r.raise_for_status()
        return r.json()["token"]
