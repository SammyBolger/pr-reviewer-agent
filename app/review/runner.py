import logging

from app.agent.graph import graph

log = logging.getLogger("pr-reviewer.runner")


async def run_review(payload: dict) -> None:
    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]
    number = pr["number"]

    log.info("reviewing %s#%s (%s)", repo, number, pr["title"])

    result = await graph.ainvoke({"payload": payload})

    review = result["review"]
    log.info(
        "posted review on %s#%s (confidence=%.2f, concerns=%d)",
        repo, number, review.confidence, len(review.concerns),
    )
