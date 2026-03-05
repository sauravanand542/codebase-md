"""Tests for codebase_md.model — all Pydantic data models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType, ServiceInfo
from codebase_md.model.convention import ConventionSet, ImportStyle, NamingConvention
from codebase_md.model.decision import DecisionRecord
from codebase_md.model.dependency import DependencyHealth, DependencyInfo
from codebase_md.model.module import APIEndpoint, FileInfo, ModuleInfo
from codebase_md.model.project import ProjectModel, ScanMetadata


class TestArchitectureModels:
    """Tests for architecture.py models."""

    def test_architecture_type_values(self) -> None:
        """Should have all expected architecture types."""
        assert ArchitectureType.MONOLITH == "monolith"
        assert ArchitectureType.CLI_TOOL == "cli_tool"
        assert ArchitectureType.UNKNOWN == "unknown"

    def test_service_info_creation(self) -> None:
        """Should create a ServiceInfo with all fields."""
        service = ServiceInfo(
            name="backend",
            path="services/backend",
            language="python",
            framework="fastapi",
            entry_point="main.py",
        )
        assert service.name == "backend"
        assert service.framework == "fastapi"

    def test_service_info_frozen(self) -> None:
        """Should be immutable."""
        service = ServiceInfo(name="api", path="api")
        with pytest.raises(ValidationError):
            service.name = "changed"  # type: ignore[misc]

    def test_architecture_info_defaults(self) -> None:
        """Should have sensible defaults."""
        info = ArchitectureInfo()
        assert info.architecture_type == ArchitectureType.UNKNOWN
        assert info.entry_points == []
        assert info.has_frontend is False
        assert info.has_ci is False

    def test_architecture_info_full(self) -> None:
        """Should accept all fields."""
        info = ArchitectureInfo(
            architecture_type=ArchitectureType.MONOREPO,
            entry_points=["src/main.py"],
            services=[ServiceInfo(name="api", path="api")],
            has_frontend=True,
            has_backend=True,
            has_database=True,
            has_docker=True,
            has_ci=True,
        )
        assert info.architecture_type == ArchitectureType.MONOREPO
        assert len(info.services) == 1


class TestConventionModels:
    """Tests for convention.py models."""

    def test_naming_convention_values(self) -> None:
        """Should have all expected naming conventions."""
        assert NamingConvention.SNAKE_CASE == "snake_case"
        assert NamingConvention.CAMEL_CASE == "camel_case"
        assert NamingConvention.PASCAL_CASE == "pascal_case"

    def test_import_style_values(self) -> None:
        """Should have all expected import styles."""
        assert ImportStyle.ABSOLUTE == "absolute"
        assert ImportStyle.RELATIVE == "relative"
        assert ImportStyle.MIXED == "mixed"

    def test_convention_set_defaults(self) -> None:
        """Should have sensible defaults."""
        conventions = ConventionSet()
        assert conventions.naming == NamingConvention.MIXED
        assert conventions.file_org == "flat"
        assert conventions.import_style == ImportStyle.MIXED

    def test_convention_set_full(self) -> None:
        """Should accept all fields."""
        conventions = ConventionSet(
            naming=NamingConvention.SNAKE_CASE,
            file_org="modular",
            import_style=ImportStyle.ABSOLUTE,
            test_pattern="test_*.py",
            patterns_used=["repository", "service"],
        )
        assert conventions.naming == NamingConvention.SNAKE_CASE
        assert len(conventions.patterns_used) == 2


class TestDecisionModel:
    """Tests for decision.py models."""

    def test_decision_record_creation(self, sample_decision: DecisionRecord) -> None:
        """Should create a DecisionRecord with all fields."""
        assert sample_decision.title == "Use Python 3.11+"
        assert sample_decision.choice == "Python 3.11+"
        assert len(sample_decision.alternatives) == 2

    def test_decision_record_frozen(self, sample_decision: DecisionRecord) -> None:
        """Should be immutable."""
        with pytest.raises(ValidationError):
            sample_decision.title = "changed"  # type: ignore[misc]

    def test_decision_record_defaults(self) -> None:
        """Should have empty lists as defaults."""
        decision = DecisionRecord(
            date=datetime(2026, 3, 4, tzinfo=UTC),
            title="Test",
            context="Testing",
            choice="Yes",
        )
        assert decision.alternatives == []
        assert decision.consequences == []


class TestDependencyModels:
    """Tests for dependency.py models."""

    def test_dependency_health_values(self) -> None:
        """Should have all expected health statuses."""
        assert DependencyHealth.HEALTHY == "healthy"
        assert DependencyHealth.DEPRECATED == "deprecated"
        assert DependencyHealth.VULNERABLE == "vulnerable"

    def test_dependency_info_creation(self, sample_dependency: DependencyInfo) -> None:
        """Should create a DependencyInfo with all fields."""
        assert sample_dependency.name == "typer"
        assert sample_dependency.ecosystem == "pypi"
        assert sample_dependency.health_score == 0.95

    def test_dependency_info_defaults(self) -> None:
        """Should have sensible defaults."""
        dep = DependencyInfo(name="test-pkg", version="1.0.0")
        assert dep.health == DependencyHealth.UNKNOWN
        assert dep.health_score == 0.0
        assert dep.ecosystem == "unknown"

    def test_dependency_info_health_score_bounds(self) -> None:
        """Should reject health scores outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            DependencyInfo(name="test", version="1.0", health_score=1.5)
        with pytest.raises(ValidationError):
            DependencyInfo(name="test", version="1.0", health_score=-0.1)


class TestModuleModels:
    """Tests for module.py models."""

    def test_file_info_creation(self, sample_file_info: FileInfo) -> None:
        """Should create a FileInfo with all fields."""
        assert sample_file_info.path == "src/app.py"
        assert sample_file_info.language == "python"
        assert "main" in sample_file_info.exports

    def test_file_info_defaults(self) -> None:
        """Should have sensible defaults."""
        f = FileInfo(path="test.py")
        assert f.language == "unknown"
        assert f.exports == []
        assert f.imports == []
        assert f.purpose == ""

    def test_api_endpoint_creation(self) -> None:
        """Should create an APIEndpoint with all fields."""
        endpoint = APIEndpoint(
            method="POST",
            path="/api/users",
            handler="views.create_user",
            auth_required=True,
        )
        assert endpoint.method == "POST"
        assert endpoint.auth_required is True

    def test_module_info_creation(self, sample_module_info: ModuleInfo) -> None:
        """Should create a ModuleInfo with all fields."""
        assert sample_module_info.name == "src"
        assert len(sample_module_info.files) == 1


class TestProjectModel:
    """Tests for project.py models."""

    def test_scan_metadata_creation(self, sample_scan_metadata: ScanMetadata) -> None:
        """Should create ScanMetadata with all fields."""
        assert sample_scan_metadata.version == "0.1.0"
        assert sample_scan_metadata.git_sha == "abc123"
        assert sample_scan_metadata.scan_duration == 1.5

    def test_project_model_creation(self, sample_project_model: ProjectModel) -> None:
        """Should create a full ProjectModel."""
        assert sample_project_model.name == "test-project"
        assert "python" in sample_project_model.languages
        assert len(sample_project_model.modules) == 1
        assert len(sample_project_model.dependencies) == 1

    def test_project_model_defaults(self) -> None:
        """Should have sensible defaults for optional fields."""
        model = ProjectModel(name="minimal", root_path="/tmp/min")
        assert model.languages == []
        assert model.modules == []
        assert model.dependencies == []
        assert model.metadata is None

    def test_project_model_frozen(self, sample_project_model: ProjectModel) -> None:
        """Should be immutable."""
        with pytest.raises(ValidationError):
            sample_project_model.name = "changed"  # type: ignore[misc]

    def test_project_model_serialization(self, sample_project_model: ProjectModel) -> None:
        """Should serialize to dict and back."""
        data = sample_project_model.model_dump(mode="json")
        restored = ProjectModel.model_validate(data)
        assert restored.name == sample_project_model.name
        assert restored.architecture.architecture_type == ArchitectureType.CLI_TOOL
        assert len(restored.modules) == 1
        assert len(restored.dependencies) == 1
