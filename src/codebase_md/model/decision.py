"""Decision record data model for architectural decision records (ADRs)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DecisionRecord(BaseModel):
    """An architectural decision record (ADR).

    Captures a significant project decision along with its context,
    alternatives considered, and expected consequences.
    """

    model_config = ConfigDict(frozen=True)

    date: datetime = Field(description="Date the decision was made")
    title: str = Field(description="Short title of the decision, e.g. 'Use PostgreSQL'")
    context: str = Field(description="Background context explaining why a decision was needed")
    choice: str = Field(description="The decision that was made")
    alternatives: list[str] = Field(
        default_factory=list,
        description="Other options that were considered",
    )
    consequences: list[str] = Field(
        default_factory=list,
        description="Expected consequences and trade-offs of the decision",
    )
