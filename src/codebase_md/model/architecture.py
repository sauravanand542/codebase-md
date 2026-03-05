"""Architecture-related data models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ArchitectureType(StrEnum):
    """Type of project architecture."""

    MONOLITH = "monolith"
    MONOREPO = "monorepo"
    MICROSERVICE = "microservice"
    LIBRARY = "library"
    CLI_TOOL = "cli_tool"
    UNKNOWN = "unknown"


class ServiceInfo(BaseModel):
    """Information about a service or sub-project in the architecture."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Service name, e.g. 'backend', 'frontend', 'api'")
    path: str = Field(description="Relative path from project root")
    language: str | None = Field(default=None, description="Primary language of this service")
    framework: str | None = Field(default=None, description="Framework used, e.g. 'fastapi'")
    entry_point: str | None = Field(default=None, description="Main entry file, e.g. 'app.py'")


class ArchitectureInfo(BaseModel):
    """Detected architecture pattern and structure of the project."""

    model_config = ConfigDict(frozen=True)

    architecture_type: ArchitectureType = Field(
        default=ArchitectureType.UNKNOWN,
        description="Detected architecture pattern",
    )
    entry_points: list[str] = Field(
        default_factory=list,
        description="Main entry point files (e.g. 'src/main.py', 'index.ts')",
    )
    services: list[ServiceInfo] = Field(
        default_factory=list,
        description="Services or sub-projects for monorepo/microservice architectures",
    )
    has_frontend: bool = Field(default=False, description="Whether a frontend exists")
    has_backend: bool = Field(default=False, description="Whether a backend exists")
    has_database: bool = Field(default=False, description="Whether database config is detected")
    has_docker: bool = Field(default=False, description="Whether Docker configuration exists")
    has_ci: bool = Field(default=False, description="Whether CI/CD configuration exists")
