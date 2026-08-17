from typing import Literal

from pydantic import BaseModel, Field, field_validator

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

    @field_validator("changes", "strengths", mode="before")
    @classmethod
    def _coerce_bullet_string(cls, v):
        # The model sometimes returns a rendered bullet string instead of a list.
        # Split on newlines and strip common bullet prefixes.
        if isinstance(v, str):
            lines = [line.strip().lstrip("-*• \t").strip() for line in v.splitlines()]
            return [line for line in lines if line]
        return v
