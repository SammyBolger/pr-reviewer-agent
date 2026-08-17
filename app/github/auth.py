import time
from functools import lru_cache

import httpx
import jwt

from app.config import settings


def app_jwt() -> str:
    now = int(time.time())
    key = settings.github_app_private_key_path.read_text()
    payload = {
        "iat": now - 60,
        "exp": now + 9 * 60,
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, key, algorithm="RS256")


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
