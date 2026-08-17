from app.review.calibrator import (
    _changed_files,
    _citation_validity,
    _context_strength,
    _diff_completeness,
    compute_confidence,
)
from app.review.schemas import Concern, Review

DIFF = """diff --git a/app/foo.py b/app/foo.py
+ hello
diff --git a/README.md b/README.md
+ world
"""


def _make_review(concerns=None, confidence=0.8, changes=None):
    return Review(
        summary="test",
        changes=changes or ["one thing"],
        concerns=concerns or [],
        confidence=confidence,
    )


def test_changed_files_extracts_paths():
    files = _changed_files(DIFF)
    assert files == {"app/foo.py", "README.md"}


def test_citation_validity_with_valid_concerns():
    r = _make_review(concerns=[
        Concern(severity="low", category="bug", file="app/foo.py", description="x"),
    ])
    assert _citation_validity(r, DIFF) == 1.0


def test_citation_validity_with_hallucinated_file():
    r = _make_review(concerns=[
        Concern(severity="low", category="bug", file="app/foo.py", description="x"),
        Concern(severity="low", category="bug", file="app/does-not-exist.py", description="y"),
    ])
    assert _citation_validity(r, DIFF) == 0.5


def test_citation_validity_no_concerns_is_full_confidence():
    r = _make_review(concerns=[])
    assert _citation_validity(r, DIFF) == 1.0


def test_diff_completeness_full():
    assert _diff_completeness("a" * 1000) == 1.0


def test_diff_completeness_truncated_drops():
    # simulate a diff bigger than MAX_DIFF_CHARS
    big = "a" * 120_000
    score = _diff_completeness(big)
    assert 0.0 < score < 1.0


def test_context_strength_scales():
    assert _context_strength([]) == 0.5
    assert _context_strength(["a", "b"]) == 0.4
    assert _context_strength(["a"] * 5) == 1.0
    assert _context_strength(["a"] * 20) == 1.0


def test_compute_confidence_returns_weighted_score():
    r = _make_review(concerns=[
        Concern(severity="low", category="bug", file="app/foo.py", description="x"),
    ])
    score, signals = compute_confidence(r, DIFF, context_chunks=["c1", "c2"])
    assert 0.0 <= score <= 1.0
    assert set(signals) == {"citation", "completeness", "context", "model"}
    assert signals["citation"] == 1.0
    assert signals["model"] == 0.8
