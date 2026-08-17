import logging

from app.github.auth import installation_token
from app.github.client import fetch_diff, post_comment
from app.llm.client import review_pr
from app.review.formatter import to_markdown

log = logging.getLogger("pr-reviewer.runner")


async def run_review(payload: dict) -> None:
    pr = payload["pull_request"]
    repo = payload["repository"]["full_name"]
    number = pr["number"]
    title = pr["title"]
    author = pr["user"]["login"]
    installation_id = payload["installation"]["id"]

    log.info("reviewing %s#%s (%s)", repo, number, title)

    token = await installation_token(installation_id)
    diff = await fetch_diff(repo, number, token)

    review = await review_pr(diff=diff, repo=repo, number=number, title=title, author=author)
    body = to_markdown(review)

    await post_comment(repo, number, body, token)
    log.info("posted review on %s#%s (confidence=%.2f, concerns=%d)",
             repo, number, review.confidence, len(review.concerns))
