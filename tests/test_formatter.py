from app.review.formatter import to_markdown
from app.review.schemas import Concern, Review


def _review(**overrides):
    defaults = dict(
        summary="one line",
        changes=["did a thing"],
        concerns=[],
        strengths=[],
        confidence=0.8,
    )
    defaults.update(overrides)
    return Review(**defaults)


def test_to_markdown_includes_summary():
    md = to_markdown(_review())
    assert "**Summary.** one line" in md


def test_to_markdown_lists_concerns_with_severity_marker():
    md = to_markdown(_review(concerns=[
        Concern(severity="high", category="security", file="app/x.py", line=42,
                description="hardcoded key", suggestion="use env var"),
    ]))
    assert "🔴" in md
    assert "**security**" in md
    assert "`app/x.py`:42" in md
    assert "_Suggested_: use env var" in md


def test_to_markdown_shows_confidence():
    md = to_markdown(_review(confidence=0.72))
    assert "_Confidence: 0.72_" in md


def test_to_markdown_shows_signals_when_provided():
    md = to_markdown(
        _review(confidence=0.72),
        signals={"citation": 1.0, "completeness": 0.9, "context": 0.6, "model": 0.75},
    )
    assert "_Signals:" in md
    assert "citation 1.00" in md


def test_to_markdown_hides_empty_sections():
    md = to_markdown(_review(changes=[], concerns=[], strengths=[]))
    assert "**What changed**" not in md
    assert "**Concerns**" not in md
    assert "**Nice work**" not in md
