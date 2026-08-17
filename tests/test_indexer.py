import base64

import httpx
import pytest
import respx

from app.retrieval.indexer import chunk_text, fetch_repo_docs, to_chunks


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.mark.asyncio
async def test_fetch_repo_docs_pulls_readme_and_walks_docs_dir():
    with respx.mock(base_url="https://api.github.com") as router:
        # README.md exists
        router.get("/repos/foo/bar/contents/README.md").mock(
            return_value=httpx.Response(200, json={
                "type": "file",
                "content": _b64("this is the readme"),
            })
        )
        # Other root candidates 404
        for path in ["README.rst", "README", "CONTRIBUTING.md", "CONTRIBUTING",
                     "ARCHITECTURE.md", "DESIGN.md", "STYLE.md", "CODE_STYLE.md"]:
            router.get(f"/repos/foo/bar/contents/{path}").mock(
                return_value=httpx.Response(404, json={"message": "not found"})
            )
        # docs dir has one markdown file
        router.get("/repos/foo/bar/contents/docs").mock(
            return_value=httpx.Response(200, json=[
                {"type": "file", "name": "guide.md", "path": "docs/guide.md"},
            ])
        )
        router.get("/repos/foo/bar/contents/docs/guide.md").mock(
            return_value=httpx.Response(200, json={
                "type": "file",
                "content": _b64("this is the guide"),
            })
        )
        router.get("/repos/foo/bar/contents/doc").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )

        docs = await fetch_repo_docs("foo/bar", "fake-token")

    ids = sorted(d["id"] for d in docs)
    assert "README.md" in ids
    assert "docs/guide.md" in ids


def test_chunk_text_splits_with_overlap():
    text = "x" * 3500
    parts = chunk_text(text, size=1000, overlap=200)
    assert len(parts) >= 3
    assert len(parts[0]) == 1000


def test_chunk_text_returns_single_when_under_size():
    assert chunk_text("short doc", size=100) == ["short doc"]


def test_to_chunks_preserves_id_and_meta():
    docs = [{"id": "README.md", "text": "x" * 5000, "meta": {"path": "README.md"}}]
    chunks = to_chunks(docs)
    assert all(c["meta"]["path"] == "README.md" for c in chunks)
    assert all(c["id"].startswith("README.md#chunk") for c in chunks)
