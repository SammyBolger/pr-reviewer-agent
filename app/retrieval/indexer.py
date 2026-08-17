import base64
import logging

import httpx

log = logging.getLogger("pr-reviewer.retrieval")

ROOT_FILES = [
    "README.md", "README.rst", "README",
    "CONTRIBUTING.md", "CONTRIBUTING",
    "ARCHITECTURE.md", "DESIGN.md",
    "STYLE.md", "CODE_STYLE.md",
]

DOCS_DIRS = ["docs", "doc"]

MAX_FILES = 40
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


async def fetch_repo_docs(repo: str, token: str) -> list[dict]:
    docs: list[dict] = []
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient() as client:
        for path in ROOT_FILES:
            doc = await _fetch_file(client, repo, path, headers)
            if doc:
                docs.append(doc)
            if len(docs) >= MAX_FILES:
                break

        for dir_name in DOCS_DIRS:
            if len(docs) >= MAX_FILES:
                break
            for path in await _walk_dir(client, repo, dir_name, headers, remaining=MAX_FILES - len(docs)):
                doc = await _fetch_file(client, repo, path, headers)
                if doc:
                    docs.append(doc)

    log.info("fetched %d docs from %s", len(docs), repo)
    return docs


async def _fetch_file(client: httpx.AsyncClient, repo: str, path: str, headers: dict) -> dict | None:
    r = await client.get(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        headers=headers,
    )
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("type") != "file" or not data.get("content"):
        return None
    try:
        text = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
    except Exception:
        return None
    return {"id": path, "text": text, "meta": {"path": path}}


async def _walk_dir(client: httpx.AsyncClient, repo: str, dir_path: str, headers: dict, remaining: int) -> list[str]:
    r = await client.get(
        f"https://api.github.com/repos/{repo}/contents/{dir_path}",
        headers=headers,
    )
    if r.status_code != 200:
        return []
    paths: list[str] = []
    for entry in r.json():
        if len(paths) >= remaining:
            break
        if entry.get("type") == "file" and entry["name"].endswith((".md", ".rst", ".txt")):
            paths.append(entry["path"])
    return paths


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += size - overlap
    return chunks


def to_chunks(docs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for doc in docs:
        parts = chunk_text(doc["text"])
        for j, part in enumerate(parts):
            out.append({
                "id": f"{doc['id']}#chunk{j}",
                "text": part,
                "meta": {"path": doc["meta"]["path"], "chunk": j},
            })
    return out
