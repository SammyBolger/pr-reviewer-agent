import logging

from langgraph.graph import END, StateGraph

from app.agent.state import ReviewState
from app.github.auth import installation_token
from app.github.client import fetch_diff, post_comment
from app.llm.client import review_pr
from app.retrieval.indexer import fetch_repo_docs, to_chunks
from app.retrieval.store import add, new_collection, query
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
        docs = await fetch_repo_docs(state["repo"], state["token"])
        if not docs:
            return {"context": []}

        collection = new_collection()
        add(collection, to_chunks(docs))

        query_text = f"{state['title']}\n\n{state['diff'][:1500]}"
        hits = query(collection, query_text, k=TOP_K)

        context = [f"[from {h['meta']['path']}]\n{h['text']}" for h in hits]
        log.info("retrieved %d context chunks for %s#%s", len(context), state["repo"], state["number"])
        return {"context": context}
    except Exception:
        log.exception("retrieval failed, continuing without context")
        return {"context": []}


async def review(state: ReviewState) -> dict:
    r = await review_pr(
        diff=state["diff"],
        repo=state["repo"],
        number=state["number"],
        title=state["title"],
        author=state["author"],
        context=state.get("context") or [],
    )
    return {"review": r, "comment_body": to_markdown(r)}


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
