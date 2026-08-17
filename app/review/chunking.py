import logging

from app.llm.client import MAX_DIFF_CHARS, ReviewOutcome, review_pr
from app.review.schemas import Review

log = logging.getLogger("pr-reviewer.chunking")


def split_diff_by_file(diff: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git ") and current:
            parts.append("".join(current))
            current = []
        current.append(line)
    if current:
        parts.append("".join(current))
    return parts


def chunk_file_diffs(file_diffs: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for fd in file_diffs:
        if current and current_size + len(fd) > max_chars:
            chunks.append("".join(current))
            current = []
            current_size = 0
        current.append(fd)
        current_size += len(fd)
    if current:
        chunks.append("".join(current))
    return chunks


async def review_pr_maybe_chunked(
    diff: str,
    repo: str,
    number: int,
    title: str,
    author: str,
    context: list[str] | None = None,
    extra_instructions: str | None = None,
) -> ReviewOutcome:
    if len(diff) <= MAX_DIFF_CHARS:
        return await review_pr(
            diff=diff, repo=repo, number=number, title=title, author=author,
            context=context, extra_instructions=extra_instructions,
        )

    files = split_diff_by_file(diff)
    chunks = chunk_file_diffs(files, max_chars=MAX_DIFF_CHARS)
    log.info("chunking large diff for %s#%s: %d chars -> %d chunks", repo, number, len(diff), len(chunks))

    outcomes: list[ReviewOutcome] = []
    for i, chunk in enumerate(chunks, start=1):
        out = await review_pr(
            diff=chunk,
            repo=repo,
            number=number,
            title=f"{title} (chunk {i}/{len(chunks)})",
            author=author,
            context=context,
            extra_instructions=extra_instructions,
        )
        outcomes.append(out)

    merged = aggregate_reviews([o.review for o in outcomes])
    return ReviewOutcome(
        review=merged,
        tokens_in=sum(o.tokens_in for o in outcomes),
        tokens_out=sum(o.tokens_out for o in outcomes),
        model=outcomes[0].model,
    )


def aggregate_reviews(reviews: list[Review]) -> Review:
    if not reviews:
        raise ValueError("no reviews to aggregate")
    if len(reviews) == 1:
        return reviews[0]

    summary = f"{reviews[0].summary} (aggregated across {len(reviews)} diff chunks)"
    return Review(
        summary=summary,
        changes=[c for r in reviews for c in r.changes],
        concerns=[c for r in reviews for c in r.concerns],
        strengths=[s for r in reviews for s in r.strengths],
        confidence=min(r.confidence for r in reviews),
    )
