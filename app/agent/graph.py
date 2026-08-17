import logging

from langgraph.graph import END, StateGraph

from app.agent.state import ReviewState
from app.github.auth import installation_token
from app.github.client import fetch_diff, post_comment
from app.llm.client import review_pr
from app.retrieval.indexer import fetch_repo_docs, to_chunks
from app.retrieval.store import add, collection_size, get_or_create_collection, query
from app.review.calibrator import compute_confidence
from app.review.formatter import to_markdown

log = logging.getLogger("pr-reviewer.agent")

TOP_K = 5


async def extract(state: ReviewState) -> dict:
    p = state["payload"]
    pr = p["pull_request"]
    return {
        "installation_id": p["installation"]["id"],
        "repo": p["repository"]["full_name"],
        "number": pr["number"],
        "title": pr["title"],
        "author": pr["user"]["login"],
    }


async def authenticate(state: ReviewState) -> dict:
    token = await installation_token(state["installation_id"])
    return {"token": token}


async def fetch(state: ReviewState) -> dict:
    diff = await fetch_diff(state["repo"], state["number"], state["token"])
    return {"diff": diff}


async def retrieve(state: ReviewState) -> dict:
    try:
        collection = get_or_create_collection(state["repo"])
        if collection_size(collection) == 0:
            docs = await fetch_repo_docs(state["repo"], state["token"])
            if not docs:
                return {"context": []}
            add(collection, to_chunks(docs))

        query_text = _build_query(state["title"], state["diff"])
        hits = query(collection, query_text, k=TOP_K)

        context = [f"[from {h['meta']['path']}]\n{h['text']}" for h in hits]
        log.info(
            "retrieved %d context chunks for %s#%s",
            len(context), state["repo"], state["number"],
        )
        return {"context": context}
    except Exception:
        log.exception("retrieval failed, continuing without context")
        return {"context": []}


def _build_query(title: str, diff: str) -> str:
    files = _changed_files(diff)
    if not files:
        return title
    file_list = "\n".join(f"- {f}" for f in files[:20])
    return f"{title}\n\nChanged files:\n{file_list}"


def _changed_files(diff: str) -> list[str]:
    seen: dict[str, None] = {}
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                seen[parts[3][2:]] = None
    return list(seen.keys())


async def review(state: ReviewState) -> dict:
    r = await review_pr(
        diff=state["diff"],
        repo=state["repo"],
        number=state["number"],
        title=state["title"],
        author=state["author"],
        context=state.get("context") or [],
    )

    model_confidence = r.confidence
    calibrated, signals = compute_confidence(r, state["diff"], state.get("context") or [])
    r.confidence = calibrated

    log.info(
        "confidence calibration for %s#%s: model=%.2f -> calibrated=%.2f (%s)",
        state["repo"], state["number"], model_confidence, calibrated,
        ", ".join(f"{k}={v:.2f}" for k, v in signals.items()),
    )

    return {
        "review": r,
        "comment_body": to_markdown(r, signals=signals),
        "confidence_signals": signals,
    }


async def post(state: ReviewState) -> dict:
    await post_comment(state["repo"], state["number"], state["comment_body"], state["token"])
    return {}


def build_graph():
    g = StateGraph(ReviewState)
    g.add_node("extract", extract)
    g.add_node("authenticate", authenticate)
    g.add_node("fetch", fetch)
    g.add_node("retrieve", retrieve)
    g.add_node("review", review)
    g.add_node("post", post)

    g.set_entry_point("extract")
    g.add_edge("extract", "authenticate")
    g.add_edge("authenticate", "fetch")
    g.add_edge("fetch", "retrieve")
    g.add_edge("retrieve", "review")
    g.add_edge("review", "post")
    g.add_edge("post", END)

    return g.compile()


graph = build_graph()
