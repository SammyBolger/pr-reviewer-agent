from typing import NamedTuple

from anthropic import AsyncAnthropic

from app.config import settings
from app.llm.prompts import SYSTEM, USER_TEMPLATE, render_context
from app.review.schemas import Review


MAX_DIFF_CHARS = 60_000

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


class ReviewOutcome(NamedTuple):
    review: Review
    tokens_in: int
    tokens_out: int
    model: str


async def review_pr(
    diff: str,
    repo: str,
    number: int,
    title: str,
    author: str,
    context: list[str] | None = None,
    extra_instructions: str | None = None,
) -> ReviewOutcome:
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n\n... (truncated, original diff was {len(diff)} chars)"

    tool = {
        "name": "submit_review",
        "description": "Submit the pull request review.",
        "input_schema": Review.model_json_schema(),
    }

    user = USER_TEMPLATE.format(
        repo=repo,
        number=number,
        title=title,
        author=author,
        context_block=render_context(context or []),
        diff=diff,
    )

    system_prompt = SYSTEM
    if extra_instructions:
        system_prompt = SYSTEM + f"\n\nAdditional guidance from this repository:\n{extra_instructions}"

    r = await _client.messages.create(
        model=settings.review_model,
        max_tokens=4000,
        system=system_prompt,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_review"},
        messages=[{"role": "user", "content": user}],
    )

    review = None
    for block in r.content:
        if block.type == "tool_use":
            review = Review.model_validate(block.input)
            break

    if review is None:
        raise RuntimeError("model did not call submit_review")

    return ReviewOutcome(
        review=review,
        tokens_in=r.usage.input_tokens,
        tokens_out=r.usage.output_tokens,
        model=r.model,
    )
