from anthropic import AsyncAnthropic

from app.config import settings
from app.evals.dataset import TestCase
from app.evals.schemas import Judgement
from app.review.schemas import Review


JUDGE_MODEL = "claude-sonnet-4-6"

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)


SYSTEM = """You are an evaluator scoring an automated code reviewer's output on a labeled test case.

You are strict but fair. You do not reward vagueness or unwarranted confidence. You do not penalize a reviewer for skipping over a truly trivial change.

Always respond by calling the submit_judgement tool.
"""


def _render_review(r: Review) -> str:
    lines = [f"Summary: {r.summary}", f"Confidence: {r.confidence:.2f}"]
    if r.changes:
        lines.append("Changes:")
        lines += [f"- {c}" for c in r.changes]
    if r.concerns:
        lines.append("Concerns:")
        for c in r.concerns:
            loc = f"{c.file}" + (f":{c.line}" if c.line else "")
            suggestion = f" Suggestion: {c.suggestion}" if c.suggestion else ""
            lines.append(f"- [{c.severity}/{c.category}] {loc}: {c.description}.{suggestion}")
    if r.strengths:
        lines.append("Strengths:")
        lines += [f"- {s}" for s in r.strengths]
    return "\n".join(lines)


async def judge(case: TestCase, review: Review) -> Judgement:
    trivial_note = ""
    if case.should_be_trivial:
        trivial_note = "\nThis test case is INTENTIONALLY TRIVIAL. A good reviewer should not manufacture concerns."

    user = f"""Test case: {case.id}
Description: {case.description}
Expected concern categories the reviewer should flag: {case.expected_categories or 'none'}
{trivial_note}

Diff under review:
{case.diff}

Reviewer's output:
{_render_review(review)}

Score the reviewer's output. Be strict."""

    tool = {
        "name": "submit_judgement",
        "description": "Submit the evaluation of the reviewer's output.",
        "input_schema": Judgement.model_json_schema(),
    }

    r = await _client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2000,
        system=SYSTEM,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_judgement"},
        messages=[{"role": "user", "content": user}],
    )

    for block in r.content:
        if block.type == "tool_use":
            return Judgement.model_validate(block.input)

    raise RuntimeError("judge did not call submit_judgement")
