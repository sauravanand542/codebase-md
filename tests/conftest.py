"""Shared test fixtures for codebase-md tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType
from codebase_md.model.convention import ConventionSet, ImportStyle, NamingConvention
from codebase_md.model.decision import DecisionRecord
from codebase_md.model.dependency import DependencyHealth, DependencyInfo
from codebase_md.model.module import APIEndpoint, FileInfo, ModuleInfo
from codebase_md.model.project import ProjectModel, ScanMetadata


@pytest.fixture
def sample_file_info() -> FileInfo:
    """A minimal FileInfo for testing."""
    return FileInfo(
        path="src/app.py",
        language="python",
        exports=["main", "App"],
        imports=["typer", "rich"],
        purpose="CLI entry point",
    )


@pytest.fixture
def sample_module_info(sample_file_info: FileInfo) -> ModuleInfo:
    """A minimal ModuleInfo for testing."""
    return ModuleInfo(
        name="src",
        path="src",
        purpose="Main source code",
        files=[sample_file_info],
        language="python",
        framework=None,
    )


@pytest.fixture
def sample_dependency() -> DependencyInfo:
    """A minimal DependencyInfo for testing."""
    return DependencyInfo(
        name="typer",
        version=">=0.9.0",
        latest="0.12.0",
        health=DependencyHealth.HEALTHY,
        health_score=0.95,
        ecosystem="pypi",
    )


@pytest.fixture
def sample_decision() -> DecisionRecord:
    """A minimal DecisionRecord for testing."""
    return DecisionRecord(
        date=datetime(2026, 3, 4, tzinfo=UTC),
        title="Use Python 3.11+",
        context="Need modern Python features",
        choice="Python 3.11+",
        alternatives=["Python 3.10", "Python 3.12"],
        consequences=["Access to StrEnum", "Wide compatibility"],
    )


@pytest.fixture
def sample_scan_metadata() -> ScanMetadata:
    """A minimal ScanMetadata for testing."""
    return ScanMetadata(
        scanned_at=datetime(2026, 3, 5, tzinfo=UTC),
        version="0.1.0",
        git_sha="abc123",
        scan_duration=1.5,
    )


@pytest.fixture
def sample_project_model(
    sample_module_info: ModuleInfo,
    sample_dependency: DependencyInfo,
    sample_decision: DecisionRecord,
    sample_scan_metadata: ScanMetadata,
) -> ProjectModel:
    """A fully populated ProjectModel for testing."""
    return ProjectModel(
        name="test-project",
        root_path="/tmp/test-project",
        languages=["python"],
        architecture=ArchitectureInfo(
            architecture_type=ArchitectureType.CLI_TOOL,
            entry_points=["src/app.py"],
            services=[],
            has_frontend=False,
            has_backend=True,
            has_database=False,
            has_docker=True,
            has_ci=True,
        ),
        modules=[sample_module_info],
        dependencies=[sample_dependency],
        conventions=ConventionSet(
            naming=NamingConvention.SNAKE_CASE,
            file_org="modular",
            import_style=ImportStyle.ABSOLUTE,
            test_pattern="test_*.py",
            patterns_used=["model", "service"],
        ),
        tech_debt=["Legacy config loader"],
        security=["No secrets in code"],
        testing=["pytest", "80% coverage"],
        decisions=[sample_decision],
        api_surface=[
            APIEndpoint(
                method="GET",
                path="/api/health",
                handler="routes.health",
                auth_required=False,
            ),
        ],
        metadata=sample_scan_metadata,
    )


@pytest.fixture
def sample_python_project(tmp_path: Path) -> Path:
    """Create a minimal Python project structure for scanning tests."""
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-proj"\nversion = "0.1.0"\n\n'
        'dependencies = [\n'
        '    "typer>=0.9.0",\n'
        '    "rich>=13.0.0",\n'
        ']\n'
    )
    # Source files
    src = tmp_path / "src" / "myapp"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text('"""My app."""\n__version__ = "0.1.0"\n')
    (src / "cli.py").write_text(
        'from __future__ import annotations\n\n'
        'import typer\n\n'
        'app = typer.Typer()\n\n\n'
        '@app.command()\n'
        'def main() -> None:\n'
        '    """Entry point."""\n'
        '    print("hello")\n'
    )
    # Test file
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_cli.py").write_text(
        'def test_placeholder() -> None:\n    assert True\n'
    )
    # Git init for git_analyzer
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return tmp_path


@pytest.fixture
def initialized_project(tmp_path: Path) -> Path:
    """Create a project with .codebase/ initialized."""
    codebase_dir = tmp_path / ".codebase"
    codebase_dir.mkdir()

    import yaml

    config = {
        "version": 1,
        "generators": ["claude", "cursor", "agents", "codex", "windsurf", "generic"],
        "scan": {"exclude": ["node_modules", ".venv"], "depth": "full"},
        "hooks": {"post_commit": True, "pre_push": False},
    }
    (codebase_dir / "config.yaml").write_text(
        yaml.dump(config, default_flow_style=False), encoding="utf-8"
    )
    return tmp_path
