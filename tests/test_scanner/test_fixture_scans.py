"""Regression tests using minimal project fixtures.

Each fixture is a tiny synthetic project (3-10 files) under
tests/fixtures/ that validates the scanner correctly detects
languages, architecture, dependencies, etc. without network access.

Run with: pytest tests/test_scanner/test_fixture_scans.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codebase_md.generators import AVAILABLE_FORMATS, get_generator
from codebase_md.model.architecture import ArchitectureType
from codebase_md.scanner.engine import ScanResult, scan_project

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _scan(fixture_name: str) -> ScanResult:
    """Scan a fixture directory.

    Args:
        fixture_name: Name of the fixture subdirectory.

    Returns:
        ScanResult.
    """
    fixture_path = FIXTURES_DIR / fixture_name
    assert fixture_path.is_dir(), f"Fixture not found: {fixture_path}"
    return scan_project(fixture_path, persist=False)


def _all_generators_produce_output(result: ScanResult) -> None:
    """Assert all generators produce non-empty output.

    Args:
        result: The scan result.
    """
    for fmt in AVAILABLE_FORMATS:
        gen = get_generator(fmt)()
        content = gen.generate(result.model)
        assert len(content) > 0, f"Generator '{fmt}' produced empty output"


# =========================================================================
# Python CLI fixture
# =========================================================================


class TestPythonCLI:
    """Tests for the python_cli fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan python_cli fixture."""
        return _scan("python_cli")

    def test_detects_python(self, result: ScanResult) -> None:
        """Should detect Python."""
        assert "python" in result.model.languages

    def test_architecture_cli_tool(self, result: ScanResult) -> None:
        """Should detect CLI tool architecture."""
        assert result.model.architecture.architecture_type == ArchitectureType.CLI_TOOL

    def test_detects_typer_dependency(self, result: ScanResult) -> None:
        """Should find typer as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "typer" in dep_names

    def test_detects_rich_dependency(self, result: ScanResult) -> None:
        """Should find rich as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "rich" in dep_names

    def test_pypi_ecosystem(self, result: ScanResult) -> None:
        """Dependencies should be pypi ecosystem."""
        ecosystems = {d.ecosystem for d in result.model.dependencies}
        assert "pypi" in ecosystems

    def test_description_extracted(self, result: ScanResult) -> None:
        """Should extract description from pyproject.toml."""
        assert "CLI" in result.model.description or "cli" in result.model.description.lower()

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Next.js app fixture
# =========================================================================


class TestNextJSApp:
    """Tests for the nextjs_app fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan nextjs_app fixture."""
        return _scan("nextjs_app")

    def test_detects_typescript(self, result: ScanResult) -> None:
        """Should detect TypeScript."""
        assert "typescript" in result.model.languages

    def test_has_npm_deps(self, result: ScanResult) -> None:
        """Should find npm dependencies."""
        ecosystems = {d.ecosystem for d in result.model.dependencies}
        assert "npm" in ecosystems

    def test_detects_next_dep(self, result: ScanResult) -> None:
        """Should find next as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "next" in dep_names

    def test_detects_react_dep(self, result: ScanResult) -> None:
        """Should find react as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "react" in dep_names

    def test_build_commands(self, result: ScanResult) -> None:
        """Should extract build commands from package.json scripts."""
        assert len(result.model.build_commands) > 0

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# FastAPI app fixture
# =========================================================================


class TestFastAPIApp:
    """Tests for the fastapi_app fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan fastapi_app fixture."""
        return _scan("fastapi_app")

    def test_detects_python(self, result: ScanResult) -> None:
        """Should detect Python."""
        assert "python" in result.model.languages

    def test_detects_fastapi_dep(self, result: ScanResult) -> None:
        """Should find fastapi as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "fastapi" in dep_names

    def test_detects_uvicorn_dep(self, result: ScanResult) -> None:
        """Should find uvicorn as a dependency."""
        dep_names = {d.name for d in result.model.dependencies}
        assert "uvicorn" in dep_names

    def test_has_entry_point(self, result: ScanResult) -> None:
        """Should find main.py as an entry point."""
        entry_points = result.model.architecture.entry_points
        assert any("main.py" in ep for ep in entry_points)

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Monorepo fixture
# =========================================================================


class TestMonorepo:
    """Tests for the monorepo fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan monorepo fixture."""
        return _scan("monorepo")

    def test_architecture_monorepo(self, result: ScanResult) -> None:
        """Should detect monorepo architecture."""
        assert result.model.architecture.architecture_type == ArchitectureType.MONOREPO

    def test_detects_typescript(self, result: ScanResult) -> None:
        """Should detect TypeScript."""
        assert "typescript" in result.model.languages

    def test_has_npm_deps(self, result: ScanResult) -> None:
        """Should find npm dependencies."""
        ecosystems = {d.ecosystem for d in result.model.dependencies}
        assert "npm" in ecosystems

    def test_has_modules(self, result: ScanResult) -> None:
        """Should detect modules."""
        assert len(result.model.modules) > 0

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Go CLI fixture
# =========================================================================


class TestGoCLI:
    """Tests for the go_cli fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan go_cli fixture."""
        return _scan("go_cli")

    def test_detects_go(self, result: ScanResult) -> None:
        """Should detect Go."""
        assert "go" in result.model.languages

    def test_has_entry_point(self, result: ScanResult) -> None:
        """Should find main.go as an entry point."""
        entry_points = result.model.architecture.entry_points
        assert any("main.go" in ep for ep in entry_points)

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Rust CLI fixture
# =========================================================================


class TestRustCLI:
    """Tests for the rust_cli fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan rust_cli fixture."""
        return _scan("rust_cli")

    def test_detects_rust(self, result: ScanResult) -> None:
        """Should detect Rust."""
        assert "rust" in result.model.languages

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Mixed language fixture
# =========================================================================


class TestMixedLang:
    """Tests for the mixed_lang fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan mixed_lang fixture."""
        return _scan("mixed_lang")

    def test_detects_python(self, result: ScanResult) -> None:
        """Should detect Python."""
        assert "python" in result.model.languages

    def test_detects_javascript(self, result: ScanResult) -> None:
        """Should detect JavaScript."""
        assert "javascript" in result.model.languages

    def test_has_both_ecosystems(self, result: ScanResult) -> None:
        """Should have both pypi and npm dependencies."""
        ecosystems = {d.ecosystem for d in result.model.dependencies}
        assert "pypi" in ecosystems
        assert "npm" in ecosystems

    def test_generators(self, result: ScanResult) -> None:
        """All generators should produce output."""
        _all_generators_produce_output(result)


# =========================================================================
# Empty repo fixture
# =========================================================================


class TestEmptyRepo:
    """Tests for the empty_repo fixture."""

    @pytest.fixture(scope="class")
    def result(self) -> ScanResult:
        """Scan empty_repo fixture."""
        return _scan("empty_repo")

    def test_no_crash(self, result: ScanResult) -> None:
        """Scanning near-empty project should not crash."""
        assert result.model is not None

    def test_no_languages(self, result: ScanResult) -> None:
        """Should detect no languages."""
        assert result.model.languages == []

    def test_no_dependencies(self, result: ScanResult) -> None:
        """Should detect no dependencies."""
        assert result.model.dependencies == []

    def test_generators_no_crash(self, result: ScanResult) -> None:
        """All generators should produce output without crashing."""
        _all_generators_produce_output(result)
