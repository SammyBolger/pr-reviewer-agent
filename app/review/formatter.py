from app.review.schemas import Review


SEVERITY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴"}


def to_markdown(review: Review) -> str:
    lines = [
        "## PR Reviewer Agent",
        "",
        f"**Summary.** {review.summary}",
        "",
    ]

    if review.changes:
        lines.append("**What changed**")
        for c in review.changes:
            lines.append(f"- {c}")
        lines.append("")

    if review.concerns:
        lines.append("**Concerns**")
        for c in review.concerns:
            marker = SEVERITY_EMOJI.get(c.severity, "")
            loc = f"`{c.file}`" + (f":{c.line}" if c.line else "")
            lines.append(f"- {marker} **{c.category}** in {loc}: {c.description}")
            if c.suggestion:
                lines.append(f"  - _Suggested_: {c.suggestion}")
        lines.append("")

    if review.strengths:
        lines.append("**Nice work**")
        for s in review.strengths:
            lines.append(f"- {s}")
        lines.append("")

    lines.append(f"_Confidence: {review.confidence:.2f}_")
    return "\n".join(lines)
