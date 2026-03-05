"""Convention-related data models for detected project conventions."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class NamingConvention(StrEnum):
    """Naming convention used in the project."""

    SNAKE_CASE = "snake_case"
    CAMEL_CASE = "camel_case"
    PASCAL_CASE = "pascal_case"
    KEBAB_CASE = "kebab_case"
    MIXED = "mixed"


class ImportStyle(StrEnum):
    """Import style used in the project."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    MIXED = "mixed"


class ConventionSet(BaseModel):
    """Detected coding conventions and patterns in the project.

    Captures the naming, file organization, import style, test patterns,
    and design patterns observed across the codebase.
    """

    model_config = ConfigDict(frozen=True)

    naming: NamingConvention = Field(
        default=NamingConvention.MIXED,
        description="Dominant naming convention detected in the codebase",
    )
    file_org: str = Field(
        default="flat",
        description="File organization pattern, e.g. 'feature-based', 'layer-based', 'flat'",
    )
    import_style: ImportStyle = Field(
        default=ImportStyle.MIXED,
        description="Dominant import style used in the codebase",
    )
    test_pattern: str = Field(
        default="",
        description="Test file naming pattern, e.g. 'test_*.py', '*.test.ts'",
    )
    patterns_used: list[str] = Field(
        default_factory=list,
        description="Design patterns detected, e.g. 'repository', 'service', 'controller'",
    )
