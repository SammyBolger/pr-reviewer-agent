from typing import TypedDict

from app.review.schemas import Review


class ReviewState(TypedDict, total=False):
    payload: dict

    installation_id: int
    repo: str
    number: int
    title: str
    author: str
    token: str

    diff: str
    context: list[str]

    review: Review
    comment_body: str
    confidence_signals: dict[str, float]
