from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["low", "medium", "high"]
Category = Literal["bug", "style", "security", "performance", "clarity", "test"]


class Concern(BaseModel):
    severity: Severity
    category: Category
    file: str
    line: int | None = None
    description: str
    suggestion: str | None = None


class Review(BaseModel):
    summary: str = Field(description="one-line summary of what the PR does")
    changes: list[str] = Field(description="bullet points of the notable changes")
    concerns: list[Concern] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
