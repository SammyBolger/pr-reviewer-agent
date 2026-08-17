from app.llm.client import MAX_DIFF_CHARS
from app.review.schemas import Review


WEIGHTS = {
    "citation": 0.40,
    "completeness": 0.20,
    "context": 0.15,
    "model": 0.25,
}


def compute_confidence(
    review: Review,
    diff: str,
    context_chunks: list[str],
) -> tuple[float, dict[str, float]]:
    signals = {
        "citation": _citation_validity(review, diff),
        "completeness": _diff_completeness(diff),
        "context": _context_strength(context_chunks),
        "model": review.confidence,
    }
    score = sum(WEIGHTS[k] * v for k, v in signals.items())
    return round(score, 2), signals


def _citation_validity(review: Review, diff: str) -> float:
    if not review.concerns:
        return 1.0
    changed = _changed_files(diff)
    if not changed:
        return 0.5
    valid = sum(1 for c in review.concerns if c.file in changed)
    return valid / len(review.concerns)


def _diff_completeness(diff: str) -> float:
    n = len(diff)
    if n == 0:
        return 0.0
    if n <= MAX_DIFF_CHARS:
        return 1.0
    return round(MAX_DIFF_CHARS / n, 2)


def _context_strength(chunks: list[str]) -> float:
    if not chunks:
        return 0.5
    return min(1.0, len(chunks) / 5)


def _changed_files(diff: str) -> set[str]:
    files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4 and parts[3].startswith("b/"):
                files.add(parts[3][2:])
    return files
