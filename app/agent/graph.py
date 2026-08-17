import logging

from langgraph.graph import END, StateGraph

from app.agent.state import ReviewState
from app.config_repo import RepoConfig, all_paths_skipped, diff_line_count, load_repo_config
from app.db.models import ReviewRecord
from app.db.session import SessionLocal
from app.github.auth import installation_token
from app.github.client import fetch_diff, post_comment
from app.retrieval.indexer import fetch_repo_docs, to_chunks
from app.retrieval.store import add, collection_size, get_or_create_collection, query
from app.review.calibrator import compute_confidence
from app.review.chunking import review_pr_maybe_chunked
from app.review.cost import estimate_cost_usd
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


async def load_config(state: ReviewState) -> dict:
    cfg = await load_repo_config(state["repo"], state["token"])
    return {"repo_config": cfg}


async def fetch(state: ReviewState) -> dict:
    diff = await fetch_diff(state["repo"], state["number"], state["token"])
    cfg: RepoConfig = state.get("repo_config") or RepoConfig()

    files = _changed_files(diff)
    if cfg.skip_paths and all_paths_skipped(files, cfg.skip_paths):
        return {"diff": diff, "skip_reason": f"all changed files match skip_paths: {cfg.skip_paths}"}

    if cfg.min_diff_lines > 0:
        lines = diff_line_count(diff)
        if lines < cfg.min_diff_lines:
            return {"diff": diff, "skip_reason": f"diff has {lines} lines, below min_diff_lines={cfg.min_diff_lines}"}

    return {"diff": diff, "skip_reason": None}


def _after_fetch(state: ReviewState) -> str:
    return "skip" if state.get("skip_reason") else "retrieve"


async def skip(state: ReviewState) -> dict:
    log.info(
        "skipping review for %s#%s: %s",
        state["repo"], state["number"], state.get("skip_reason"),
    )
    return {}


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
    cfg: RepoConfig = state.get("repo_config") or RepoConfig()

    outcome = await review_pr_maybe_chunked(
        diff=state["diff"],
        repo=state["repo"],
        number=state["number"],
        title=state["title"],
        author=state["author"],
        context=state.get("context") or [],
        extra_instructions=cfg.extra_instructions,
    )
    r = outcome.review

    model_confidence = r.confidence
    calibrated, signals = compute_confidence(r, state["diff"], state.get("context") or [])
    r.confidence = calibrated

    cost = estimate_cost_usd(outcome.model, outcome.tokens_in, outcome.tokens_out)

    log.info(
        "review %s#%s: model=%.2f->%.2f tokens=%d+%d cost=$%.4f",
        state["repo"], state["number"], model_confidence, calibrated,
        outcome.tokens_in, outcome.tokens_out, cost,
    )

    await _save_record(state, r, outcome, cost)

    return {
        "review": r,
        "comment_body": to_markdown(r, signals=signals),
        "confidence_signals": signals,
    }


async def _save_record(state: ReviewState, r, outcome, cost: float) -> None:
    try:
        async with SessionLocal() as session:
            session.add(ReviewRecord(
                repo=state["repo"],
                pr_number=state["number"],
                model=outcome.model,
                tokens_in=outcome.tokens_in,
                tokens_out=outcome.tokens_out,
                cost_usd=cost,
                confidence=r.confidence,
                num_concerns=len(r.concerns),
            ))
            await session.commit()
    except Exception:
        log.exception("failed to save review record (non-fatal)")


async def post(state: ReviewState) -> dict:
    await post_comment(state["repo"], state["number"], state["comment_body"], state["token"])
    return {}


def build_graph():
    g = StateGraph(ReviewState)
    g.add_node("extract", extract)
    g.add_node("authenticate", authenticate)
    g.add_node("load_config", load_config)
    g.add_node("fetch", fetch)
    g.add_node("skip", skip)
    g.add_node("retrieve", retrieve)
    g.add_node("review", review)
    g.add_node("post", post)

    g.set_entry_point("extract")
    g.add_edge("extract", "authenticate")
    g.add_edge("authenticate", "load_config")
    g.add_edge("load_config", "fetch")
    g.add_conditional_edges("fetch", _after_fetch, {"skip": "skip", "retrieve": "retrieve"})
    g.add_edge("skip", END)
    g.add_edge("retrieve", "review")
    g.add_edge("review", "post")
    g.add_edge("post", END)

    return g.compile()


graph = build_graph()
