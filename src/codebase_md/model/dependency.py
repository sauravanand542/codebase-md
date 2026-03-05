"""Dependency-related data models for package dependency tracking."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DependencyHealth(StrEnum):
    """Health status of a dependency."""

    HEALTHY = "healthy"
    OUTDATED = "outdated"
    VULNERABLE = "vulnerable"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


class DependencyInfo(BaseModel):
    """Information about a project dependency.

    Tracks the current version, latest available version, health status,
    and where in the codebase the dependency is used.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Package name, e.g. 'react', 'fastapi'")
    version: str = Field(description="Currently installed version constraint")
    latest: str | None = Field(
        default=None,
        description="Latest version available from the registry",
    )
    health: DependencyHealth = Field(
        default=DependencyHealth.UNKNOWN,
        description="Health status of the dependency",
    )
    health_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Health score from 0.0 (critical) to 1.0 (healthy)",
    )
    usage_locations: list[str] = Field(
        default_factory=list,
        description="File paths where this dependency is imported or used",
    )
    breaking_changes: list[str] = Field(
        default_factory=list,
        description="Known breaking changes between current and latest version",
    )
    ecosystem: str = Field(
        default="unknown",
        description="Package ecosystem, e.g. 'npm', 'pypi', 'cargo'",
    )
