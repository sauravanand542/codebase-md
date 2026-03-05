"""Pydantic data models for codebase-md."""

from __future__ import annotations

from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType
from codebase_md.model.convention import (
    ConventionSet,
    ImportStyle,
    NamingConvention,
)
from codebase_md.model.decision import DecisionRecord
from codebase_md.model.dependency import DependencyHealth, DependencyInfo
from codebase_md.model.module import APIEndpoint, FileInfo, ModuleInfo
from codebase_md.model.project import GitInsights, ProjectModel, ScanMetadata

__all__ = [
    "APIEndpoint",
    "ArchitectureInfo",
    "ArchitectureType",
    "ConventionSet",
    "DecisionRecord",
    "DependencyHealth",
    "DependencyInfo",
    "FileInfo",
    "GitInsights",
    "ImportStyle",
    "ModuleInfo",
    "NamingConvention",
    "ProjectModel",
    "ScanMetadata",
]
