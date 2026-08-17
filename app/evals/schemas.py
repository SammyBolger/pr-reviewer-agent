from typing import Literal

from pydantic import BaseModel, Field


class Judgement(BaseModel):
    detection_score: int = Field(ge=0, le=5, description="0=missed all expected issues, 5=caught them all")
    false_positive_score: int = Field(ge=0, le=5, description="5=no invalid concerns, 0=all concerns are noise")
    usefulness_score: int = Field(ge=0, le=5, description="Would a developer be helped by this review?")
    calibration_score: int = Field(ge=0, le=5, description="Is the review's confidence appropriate for what it saw?")
    missed_issues: list[str] = Field(default_factory=list)
    invalid_concerns: list[str] = Field(default_factory=list)
    verdict: Literal["pass", "borderline", "fail"]
    notes: str
