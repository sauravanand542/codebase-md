"""Tests for codebase_md.scanner.differ — diff engine."""

from __future__ import annotations

from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType
from codebase_md.model.convention import ConventionSet, ImportStyle, NamingConvention
from codebase_md.model.dependency import DependencyHealth, DependencyInfo
from codebase_md.model.module import FileInfo, ModuleInfo
from codebase_md.model.project import ProjectModel
from codebase_md.scanner.differ import (
    ConventionChange,
    DependencyChange,
    DiffResult,
    ModuleChange,
    compute_diff,
    format_diff,
)


def _make_model(
    name: str = "test",
    languages: list[str] | None = None,
    modules: list[ModuleInfo] | None = None,
    dependencies: list[DependencyInfo] | None = None,
    conventions: ConventionSet | None = None,
    architecture: ArchitectureInfo | None = None,
) -> ProjectModel:
    """Helper to create a ProjectModel with sensible defaults."""
    return ProjectModel(
        name=name,
        root_path="/tmp/test",
        languages=languages or ["python"],
        modules=modules or [],
        dependencies=dependencies or [],
        conventions=conventions or ConventionSet(),
        architecture=architecture or ArchitectureInfo(),
    )


class TestComputeDiffNoChanges:
    """Tests for compute_diff when models are identical."""

    def test_identical_models_no_changes(self) -> None:
        """Same model should produce no changes."""
        model = _make_model()
        result = compute_diff(model, model)
        assert not result.has_changes
        assert result.summary == "No changes detected"

    def test_identical_with_modules(self) -> None:
        """Same model with modules should produce no changes."""
        mod = ModuleInfo(
            name="src",
            path="src",
            purpose="Source",
            files=[FileInfo(path="src/app.py", language="python")],
        )
        model = _make_model(modules=[mod])
        result = compute_diff(model, model)
        assert not result.has_changes


class TestComputeDiffLanguages:
    """Tests for language change detection."""

    def test_added_language(self) -> None:
        """Should detect added languages."""
        old = _make_model(languages=["python"])
        new = _make_model(languages=["python", "javascript"])
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.added_languages == ["javascript"]
        assert not result.removed_languages

    def test_removed_language(self) -> None:
        """Should detect removed languages."""
        old = _make_model(languages=["python", "javascript"])
        new = _make_model(languages=["python"])
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.removed_languages == ["javascript"]
        assert not result.added_languages


class TestComputeDiffModules:
    """Tests for module change detection."""

    def test_added_module(self) -> None:
        """Should detect added modules."""
        mod = ModuleInfo(name="new_mod", path="new_mod", purpose="New")
        old = _make_model(modules=[])
        new = _make_model(modules=[mod])
        result = compute_diff(old, new)
        assert result.has_changes
        assert len(result.module_changes) == 1
        assert result.module_changes[0].change_type == "added"
        assert result.module_changes[0].name == "new_mod"

    def test_removed_module(self) -> None:
        """Should detect removed modules."""
        mod = ModuleInfo(name="old_mod", path="old_mod", purpose="Old")
        old = _make_model(modules=[mod])
        new = _make_model(modules=[])
        result = compute_diff(old, new)
        assert result.has_changes
        assert len(result.module_changes) == 1
        assert result.module_changes[0].change_type == "removed"

    def test_modified_module_file_count(self) -> None:
        """Should detect modified modules (file count change)."""
        old_mod = ModuleInfo(
            name="src",
            path="src",
            purpose="Source",
            files=[FileInfo(path="src/a.py", language="python")],
        )
        new_mod = ModuleInfo(
            name="src",
            path="src",
            purpose="Source",
            files=[
                FileInfo(path="src/a.py", language="python"),
                FileInfo(path="src/b.py", language="python"),
            ],
        )
        old = _make_model(modules=[old_mod])
        new = _make_model(modules=[new_mod])
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.module_changes[0].change_type == "modified"
        assert "files:" in result.module_changes[0].details


class TestComputeDiffDependencies:
    """Tests for dependency change detection."""

    def test_added_dependency(self) -> None:
        """Should detect added dependencies."""
        dep = DependencyInfo(
            name="requests",
            version="2.31.0",
            health=DependencyHealth.HEALTHY,
            ecosystem="pypi",
        )
        old = _make_model(dependencies=[])
        new = _make_model(dependencies=[dep])
        result = compute_diff(old, new)
        assert result.has_changes
        assert len(result.dependency_changes) == 1
        assert result.dependency_changes[0].change_type == "added"
        assert result.dependency_changes[0].name == "requests"

    def test_removed_dependency(self) -> None:
        """Should detect removed dependencies."""
        dep = DependencyInfo(
            name="flask",
            version="3.0.0",
            health=DependencyHealth.HEALTHY,
            ecosystem="pypi",
        )
        old = _make_model(dependencies=[dep])
        new = _make_model(dependencies=[])
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.dependency_changes[0].change_type == "removed"

    def test_version_changed(self) -> None:
        """Should detect version changes."""
        old_dep = DependencyInfo(
            name="typer",
            version="0.9.0",
            health=DependencyHealth.HEALTHY,
            ecosystem="pypi",
        )
        new_dep = DependencyInfo(
            name="typer",
            version="0.12.0",
            health=DependencyHealth.HEALTHY,
            ecosystem="pypi",
        )
        old = _make_model(dependencies=[old_dep])
        new = _make_model(dependencies=[new_dep])
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.dependency_changes[0].change_type == "version_changed"
        assert result.dependency_changes[0].old_version == "0.9.0"
        assert result.dependency_changes[0].new_version == "0.12.0"


class TestComputeDiffConventions:
    """Tests for convention change detection."""

    def test_naming_convention_changed(self) -> None:
        """Should detect naming convention change."""
        old_conv = ConventionSet(naming=NamingConvention.SNAKE_CASE)
        new_conv = ConventionSet(naming=NamingConvention.CAMEL_CASE)
        old = _make_model(conventions=old_conv)
        new = _make_model(conventions=new_conv)
        result = compute_diff(old, new)
        assert result.has_changes
        assert any(c.field == "naming" for c in result.convention_changes)

    def test_import_style_changed(self) -> None:
        """Should detect import style change."""
        old_conv = ConventionSet(import_style=ImportStyle.ABSOLUTE)
        new_conv = ConventionSet(import_style=ImportStyle.RELATIVE)
        old = _make_model(conventions=old_conv)
        new = _make_model(conventions=new_conv)
        result = compute_diff(old, new)
        assert result.has_changes
        assert any(c.field == "import_style" for c in result.convention_changes)


class TestComputeDiffArchitecture:
    """Tests for architecture change detection."""

    def test_architecture_type_changed(self) -> None:
        """Should detect architecture type change."""
        old_arch = ArchitectureInfo(architecture_type=ArchitectureType.MONOLITH)
        new_arch = ArchitectureInfo(architecture_type=ArchitectureType.MONOREPO)
        old = _make_model(architecture=old_arch)
        new = _make_model(architecture=new_arch)
        result = compute_diff(old, new)
        assert result.has_changes
        assert result.architecture_changed
        assert result.old_architecture == "monolith"
        assert result.new_architecture == "monorepo"

    def test_same_architecture(self) -> None:
        """Should not flag when architecture type is same."""
        arch = ArchitectureInfo(architecture_type=ArchitectureType.CLI_TOOL)
        old = _make_model(architecture=arch)
        new = _make_model(architecture=arch)
        result = compute_diff(old, new)
        assert not result.architecture_changed


class TestFormatDiff:
    """Tests for format_diff output."""

    def test_no_changes_message(self) -> None:
        """Should return 'No changes' message."""
        result = DiffResult(has_changes=False)
        output = format_diff(result)
        assert "No changes" in output

    def test_format_with_changes(self) -> None:
        """Should format all change types."""
        result = DiffResult(
            has_changes=True,
            added_languages=["typescript"],
            removed_languages=["go"],
            module_changes=[
                ModuleChange(name="api", change_type="added", details="New module"),
            ],
            dependency_changes=[
                DependencyChange(
                    name="react",
                    change_type="added",
                    new_version="19.0.0",
                ),
            ],
            convention_changes=[
                ConventionChange(
                    field="naming",
                    old_value="snake_case",
                    new_value="camel_case",
                ),
            ],
            architecture_changed=True,
            old_architecture="monolith",
            new_architecture="monorepo",
            file_count_old=10,
            file_count_new=15,
            summary="test",
        )
        output = format_diff(result)
        assert "Languages" in output
        assert "+ typescript" in output
        assert "- go" in output
        assert "Modules" in output
        assert "+ api" in output
        assert "Dependencies" in output
        assert "react" in output
        assert "Conventions" in output
        assert "naming" in output
        assert "monolith" in output
        assert "monorepo" in output
        assert "10" in output
        assert "15" in output


class TestDiffResultModel:
    """Tests for DiffResult Pydantic model."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        result = DiffResult(has_changes=False)
        assert not result.has_changes
        assert result.added_languages == []
        assert result.removed_languages == []
        assert result.module_changes == []
        assert result.dependency_changes == []
        assert result.convention_changes == []
        assert not result.architecture_changed
        assert result.summary == ""

    def test_frozen(self) -> None:
        """DiffResult should be frozen."""
        result = DiffResult(has_changes=False)
        try:
            result.has_changes = True  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except Exception:
            pass
