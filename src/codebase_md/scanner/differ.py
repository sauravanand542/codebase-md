"""Diff engine — compare two ProjectModel instances to detect changes.

Compares a previous scan (from .codebase/project.json) with a fresh scan
and produces a structured DiffResult highlighting additions, removals,
and modifications across all project dimensions.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from codebase_md.model.project import ProjectModel


class ModuleChange(BaseModel):
    """Represents a change in a module between two scans."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Module name")
    change_type: str = Field(description="added, removed, or modified")
    details: str = Field(default="", description="Human-readable description of the change")


class DependencyChange(BaseModel):
    """Represents a change in a dependency between two scans."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Dependency name")
    change_type: str = Field(description="added, removed, or version_changed")
    old_version: str | None = Field(default=None, description="Previous version")
    new_version: str | None = Field(default=None, description="New version")


class ConventionChange(BaseModel):
    """Represents a change in detected conventions."""

    model_config = ConfigDict(frozen=True)

    field: str = Field(description="Convention field that changed")
    old_value: str = Field(description="Previous value")
    new_value: str = Field(description="New value")


class DiffResult(BaseModel):
    """Complete diff between two ProjectModel snapshots.

    Contains all detected changes across languages, modules,
    dependencies, conventions, and architecture.
    """

    model_config = ConfigDict(frozen=True)

    has_changes: bool = Field(description="Whether any changes were detected")
    added_languages: list[str] = Field(default_factory=list)
    removed_languages: list[str] = Field(default_factory=list)
    module_changes: list[ModuleChange] = Field(default_factory=list)
    dependency_changes: list[DependencyChange] = Field(default_factory=list)
    convention_changes: list[ConventionChange] = Field(default_factory=list)
    architecture_changed: bool = Field(default=False)
    old_architecture: str | None = Field(default=None)
    new_architecture: str | None = Field(default=None)
    file_count_old: int = Field(default=0, description="Total files in old scan")
    file_count_new: int = Field(default=0, description="Total files in new scan")
    summary: str = Field(default="", description="Human-readable summary of changes")


class DifferError(Exception):
    """Raised when diff computation fails."""


def compute_diff(old: ProjectModel, new: ProjectModel) -> DiffResult:
    """Compare two ProjectModel instances and produce a DiffResult.

    Args:
        old: The previous scan result (from .codebase/project.json).
        new: The fresh scan result.

    Returns:
        DiffResult with all detected changes.
    """
    added_langs = [lang for lang in new.languages if lang not in old.languages]
    removed_langs = [lang for lang in old.languages if lang not in new.languages]

    module_changes = _diff_modules(old, new)
    dep_changes = _diff_dependencies(old, new)
    conv_changes = _diff_conventions(old, new)

    arch_changed = (
        old.architecture.architecture_type != new.architecture.architecture_type
    )
    old_arch = old.architecture.architecture_type.value if arch_changed else None
    new_arch = new.architecture.architecture_type.value if arch_changed else None

    old_file_count = sum(len(m.files) for m in old.modules)
    new_file_count = sum(len(m.files) for m in new.modules)

    has_changes = bool(
        added_langs
        or removed_langs
        or module_changes
        or dep_changes
        or conv_changes
        or arch_changed
    )

    # Build summary
    parts: list[str] = []
    if added_langs:
        parts.append(f"+{len(added_langs)} language(s)")
    if removed_langs:
        parts.append(f"-{len(removed_langs)} language(s)")
    if module_changes:
        added_m = sum(1 for m in module_changes if m.change_type == "added")
        removed_m = sum(1 for m in module_changes if m.change_type == "removed")
        modified_m = sum(1 for m in module_changes if m.change_type == "modified")
        if added_m:
            parts.append(f"+{added_m} module(s)")
        if removed_m:
            parts.append(f"-{removed_m} module(s)")
        if modified_m:
            parts.append(f"~{modified_m} module(s) modified")
    if dep_changes:
        added_d = sum(1 for d in dep_changes if d.change_type == "added")
        removed_d = sum(1 for d in dep_changes if d.change_type == "removed")
        changed_d = sum(1 for d in dep_changes if d.change_type == "version_changed")
        if added_d:
            parts.append(f"+{added_d} dep(s)")
        if removed_d:
            parts.append(f"-{removed_d} dep(s)")
        if changed_d:
            parts.append(f"~{changed_d} dep version(s)")
    if conv_changes:
        parts.append(f"~{len(conv_changes)} convention(s)")
    if arch_changed:
        parts.append(f"architecture: {old_arch} → {new_arch}")

    summary = ", ".join(parts) if parts else "No changes detected"

    return DiffResult(
        has_changes=has_changes,
        added_languages=added_langs,
        removed_languages=removed_langs,
        module_changes=module_changes,
        dependency_changes=dep_changes,
        convention_changes=conv_changes,
        architecture_changed=arch_changed,
        old_architecture=old_arch,
        new_architecture=new_arch,
        file_count_old=old_file_count,
        file_count_new=new_file_count,
        summary=summary,
    )


def _diff_modules(old: ProjectModel, new: ProjectModel) -> list[ModuleChange]:
    """Compare modules between two scans.

    Args:
        old: Previous project model.
        new: Current project model.

    Returns:
        List of module changes.
    """
    old_names = {m.name for m in old.modules}
    new_names = {m.name for m in new.modules}

    changes: list[ModuleChange] = []

    # Added modules
    for name in sorted(new_names - old_names):
        mod = next(m for m in new.modules if m.name == name)
        changes.append(
            ModuleChange(
                name=name,
                change_type="added",
                details=f"New module with {len(mod.files)} file(s)",
            )
        )

    # Removed modules
    for name in sorted(old_names - new_names):
        mod = next(m for m in old.modules if m.name == name)
        changes.append(
            ModuleChange(
                name=name,
                change_type="removed",
                details=f"Removed module (had {len(mod.files)} file(s))",
            )
        )

    # Modified modules (same name but different file count or language)
    for name in sorted(old_names & new_names):
        old_mod = next(m for m in old.modules if m.name == name)
        new_mod = next(m for m in new.modules if m.name == name)
        diffs: list[str] = []
        if len(old_mod.files) != len(new_mod.files):
            diffs.append(f"files: {len(old_mod.files)} → {len(new_mod.files)}")
        if old_mod.language != new_mod.language:
            diffs.append(f"language: {old_mod.language or '?'} → {new_mod.language or '?'}")
        if old_mod.framework != new_mod.framework:
            diffs.append(f"framework: {old_mod.framework or '?'} → {new_mod.framework or '?'}")
        if diffs:
            changes.append(
                ModuleChange(
                    name=name,
                    change_type="modified",
                    details="; ".join(diffs),
                )
            )

    return changes


def _diff_dependencies(
    old: ProjectModel, new: ProjectModel
) -> list[DependencyChange]:
    """Compare dependencies between two scans.

    Args:
        old: Previous project model.
        new: Current project model.

    Returns:
        List of dependency changes.
    """
    old_deps = {d.name: d for d in old.dependencies}
    new_deps = {d.name: d for d in new.dependencies}

    changes: list[DependencyChange] = []

    # Added
    for name in sorted(set(new_deps) - set(old_deps)):
        changes.append(
            DependencyChange(
                name=name,
                change_type="added",
                new_version=new_deps[name].version,
            )
        )

    # Removed
    for name in sorted(set(old_deps) - set(new_deps)):
        changes.append(
            DependencyChange(
                name=name,
                change_type="removed",
                old_version=old_deps[name].version,
            )
        )

    # Version changed
    for name in sorted(set(old_deps) & set(new_deps)):
        if old_deps[name].version != new_deps[name].version:
            changes.append(
                DependencyChange(
                    name=name,
                    change_type="version_changed",
                    old_version=old_deps[name].version,
                    new_version=new_deps[name].version,
                )
            )

    return changes


def _diff_conventions(
    old: ProjectModel, new: ProjectModel
) -> list[ConventionChange]:
    """Compare detected conventions between two scans.

    Args:
        old: Previous project model.
        new: Current project model.

    Returns:
        List of convention changes.
    """
    changes: list[ConventionChange] = []

    old_conv = old.conventions
    new_conv = new.conventions

    if old_conv.naming.value != new_conv.naming.value:
        changes.append(
            ConventionChange(
                field="naming",
                old_value=old_conv.naming.value,
                new_value=new_conv.naming.value,
            )
        )

    if old_conv.import_style.value != new_conv.import_style.value:
        changes.append(
            ConventionChange(
                field="import_style",
                old_value=old_conv.import_style.value,
                new_value=new_conv.import_style.value,
            )
        )

    if (old_conv.file_org or "") != (new_conv.file_org or ""):
        changes.append(
            ConventionChange(
                field="file_org",
                old_value=old_conv.file_org or "unknown",
                new_value=new_conv.file_org or "unknown",
            )
        )

    if (old_conv.test_pattern or "") != (new_conv.test_pattern or ""):
        changes.append(
            ConventionChange(
                field="test_pattern",
                old_value=old_conv.test_pattern or "unknown",
                new_value=new_conv.test_pattern or "unknown",
            )
        )

    old_patterns = set(old_conv.patterns_used)
    new_patterns = set(new_conv.patterns_used)
    if old_patterns != new_patterns:
        changes.append(
            ConventionChange(
                field="patterns_used",
                old_value=", ".join(sorted(old_patterns)) or "none",
                new_value=", ".join(sorted(new_patterns)) or "none",
            )
        )

    return changes


def format_diff(diff: DiffResult) -> str:
    """Format a DiffResult as a human-readable string.

    Args:
        diff: The diff result to format.

    Returns:
        Formatted markdown-style string.
    """
    if not diff.has_changes:
        return "No changes since last scan."

    lines: list[str] = ["## Changes Since Last Scan", ""]

    if diff.architecture_changed:
        lines.append(
            f"**Architecture:** {diff.old_architecture} → {diff.new_architecture}"
        )
        lines.append("")

    if diff.added_languages or diff.removed_languages:
        lines.append("### Languages")
        for lang in diff.added_languages:
            lines.append(f"  + {lang}")
        for lang in diff.removed_languages:
            lines.append(f"  - {lang}")
        lines.append("")

    if diff.module_changes:
        lines.append("### Modules")
        for mc in diff.module_changes:
            prefix = {"added": "+", "removed": "-", "modified": "~"}.get(
                mc.change_type, "?"
            )
            detail = f" — {mc.details}" if mc.details else ""
            lines.append(f"  {prefix} {mc.name}{detail}")
        lines.append("")

    if diff.dependency_changes:
        lines.append("### Dependencies")
        for dc in diff.dependency_changes:
            if dc.change_type == "added":
                lines.append(f"  + {dc.name} ({dc.new_version})")
            elif dc.change_type == "removed":
                lines.append(f"  - {dc.name} ({dc.old_version})")
            else:
                lines.append(
                    f"  ~ {dc.name}: {dc.old_version} → {dc.new_version}"
                )
        lines.append("")

    if diff.convention_changes:
        lines.append("### Conventions")
        for cc in diff.convention_changes:
            lines.append(f"  ~ {cc.field}: {cc.old_value} → {cc.new_value}")
        lines.append("")

    file_diff = diff.file_count_new - diff.file_count_old
    if file_diff != 0:
        sign = "+" if file_diff > 0 else ""
        lines.append(
            f"**Files:** {diff.file_count_old} → {diff.file_count_new} ({sign}{file_diff})"
        )

    return "\n".join(lines)
