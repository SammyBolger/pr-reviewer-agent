from anthropic import AsyncAnthropic

from app.config import settings
from app.llm.prompts import SYSTEM, USER_TEMPLATE
from app.review.schemas import Review


MAX_DIFF_CHARS = 60_000

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def review_pr(diff: str, repo: str, number: int, title: str, author: str) -> Review:
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n\n... (truncated, original diff was {len(diff)} chars)"

    tool = {
        "name": "submit_review",
        "description": "Submit the pull request review.",
        "input_schema": Review.model_json_schema(),
    }

    user = USER_TEMPLATE.format(repo=repo, number=number, title=title, author=author, diff=diff)

    r = await _client.messages.create(
        model=settings.review_model,
        max_tokens=4000,
        system=SYSTEM,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_review"},
        messages=[{"role": "user", "content": user}],
    )

    for block in r.content:
        if block.type == "tool_use":
            return Review.model_validate(block.input)

    raise RuntimeError("model did not call submit_review")
