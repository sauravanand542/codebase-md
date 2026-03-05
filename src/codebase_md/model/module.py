"""Module and file-level data models for codebase structure."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FileInfo(BaseModel):
    """Information about a single source file.

    Captures the file path, detected language, exported symbols,
    imported dependencies, and inferred purpose.
    """

    model_config = ConfigDict(frozen=True)

    path: str = Field(description="Relative path from project root")
    language: str = Field(
        default="unknown",
        description="Detected programming language, e.g. 'python', 'typescript'",
    )
    exports: list[str] = Field(
        default_factory=list,
        description="Symbols exported from this file (functions, classes, constants)",
    )
    imports: list[str] = Field(
        default_factory=list,
        description="Modules or packages imported by this file",
    )
    purpose: str = Field(
        default="",
        description="Inferred purpose of this file, e.g. 'API routes', 'database models'",
    )


class APIEndpoint(BaseModel):
    """Information about a detected API endpoint.

    Represents an HTTP endpoint found in route definitions
    (Express, FastAPI, Django URLs, etc.).
    """

    model_config = ConfigDict(frozen=True)

    method: str = Field(description="HTTP method, e.g. 'GET', 'POST', 'PUT', 'DELETE'")
    path: str = Field(description="URL path, e.g. '/api/users'")
    handler: str = Field(
        default="",
        description="Handler function or class reference, e.g. 'views.UserView'",
    )
    auth_required: bool = Field(
        default=False,
        description="Whether authentication is required for this endpoint",
    )


class ModuleInfo(BaseModel):
    """Information about a logical module or package in the project.

    A module represents a logical grouping of related files, such as
    'backend', 'frontend', 'shared', or a specific feature area.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Module name, e.g. 'backend', 'auth', 'shared'")
    path: str = Field(description="Relative path from project root to module directory")
    purpose: str = Field(
        default="",
        description="Inferred purpose of this module",
    )
    files: list[FileInfo] = Field(
        default_factory=list,
        description="Files belonging to this module",
    )
    language: str | None = Field(
        default=None,
        description="Primary language of this module",
    )
    framework: str | None = Field(
        default=None,
        description="Framework used in this module, e.g. 'fastapi', 'nextjs'",
    )
