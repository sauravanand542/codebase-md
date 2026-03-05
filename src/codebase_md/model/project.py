"""Root project model — the central data structure for codebase-md."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from codebase_md.model.architecture import ArchitectureInfo
from codebase_md.model.convention import ConventionSet
from codebase_md.model.decision import DecisionRecord
from codebase_md.model.dependency import DependencyInfo
from codebase_md.model.module import APIEndpoint, ModuleInfo


class ScanMetadata(BaseModel):
    """Metadata about when and how the scan was performed.

    Tracks the scan timestamp, tool version, git SHA of the scanned
    project, and how long the scan took.
    """

    model_config = ConfigDict(frozen=True)

    scanned_at: datetime = Field(description="Timestamp when the scan was performed")
    version: str = Field(description="Version of codebase-md that performed the scan")
    git_sha: str | None = Field(
        default=None,
        description="Git SHA of the scanned project at scan time",
    )
    scan_duration: float = Field(
        default=0.0,
        ge=0.0,
        description="Duration of the scan in seconds",
    )


class ProjectModel(BaseModel):
    """Root data model representing a fully scanned project.

    This is the central data structure that flows through the entire
    pipeline: Scanner Engine → ProjectModel → Generators → Output Files.
    Every generator receives this model and transforms it into the
    appropriate output format.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Project name")
    root_path: str = Field(description="Absolute path to the project root directory")
    languages: list[str] = Field(
        default_factory=list,
        description="Programming languages detected in the project",
    )
    architecture: ArchitectureInfo = Field(
        default_factory=ArchitectureInfo,
        description="Detected architecture pattern and structure",
    )
    modules: list[ModuleInfo] = Field(
        default_factory=list,
        description="Logical modules or packages in the project",
    )
    dependencies: list[DependencyInfo] = Field(
        default_factory=list,
        description="Project dependencies with health information",
    )
    conventions: ConventionSet = Field(
        default_factory=ConventionSet,
        description="Detected coding conventions and patterns",
    )
    tech_debt: list[str] = Field(
        default_factory=list,
        description="Identified tech debt items",
    )
    security: list[str] = Field(
        default_factory=list,
        description="Security observations and concerns",
    )
    testing: list[str] = Field(
        default_factory=list,
        description="Testing framework and coverage information",
    )
    decisions: list[DecisionRecord] = Field(
        default_factory=list,
        description="Architectural decision records",
    )
    api_surface: list[APIEndpoint] = Field(
        default_factory=list,
        description="Detected API endpoints",
    )
    metadata: ScanMetadata | None = Field(
        default=None,
        description="Metadata about the scan that produced this model",
    )
