import base64
import fnmatch
import logging

import httpx
import yaml
from pydantic import BaseModel, Field

log = logging.getLogger("pr-reviewer.config_repo")

CONFIG_PATHS = [".reviewbot.yml", ".reviewbot.yaml"]


class RepoConfig(BaseModel):
    skip_paths: list[str] = Field(default_factory=list)
    min_diff_lines: int = 0
    extra_instructions: str | None = None


_cache: dict[str, RepoConfig] = {}


async def load_repo_config(repo: str, token: str) -> RepoConfig:
    if repo in _cache:
        return _cache[repo]

    cfg = await _fetch(repo, token)
    _cache[repo] = cfg
    return cfg


async def _fetch(repo: str, token: str) -> RepoConfig:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        for path in CONFIG_PATHS:
            r = await client.get(
                f"https://api.github.com/repos/{repo}/contents/{path}",
                headers=headers,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get("type") != "file":
                continue
            try:
                raw = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
                parsed = yaml.safe_load(raw) or {}
                cfg = RepoConfig.model_validate(parsed)
                log.info("loaded .reviewbot config for %s", repo)
                return cfg
            except Exception:
                log.exception("failed to parse %s in %s", path, repo)
                break

    return RepoConfig()


def all_paths_skipped(changed_files: list[str], skip_patterns: list[str]) -> bool:
    if not changed_files or not skip_patterns:
        return False
    for f in changed_files:
        if not any(fnmatch.fnmatch(f, pat) for pat in skip_patterns):
            return False
    return True


def diff_line_count(diff: str) -> int:
    count = 0
    for line in diff.splitlines():
        is_added = line.startswith("+") and not line.startswith("+++")
        is_removed = line.startswith("-") and not line.startswith("---")
        if is_added or is_removed:
            count += 1
    return count


def invalidate_cache(repo: str) -> None:
    _cache.pop(repo, None)
