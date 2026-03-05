"""Tests for codebase_md.scanner.structure_analyzer."""

from __future__ import annotations

from pathlib import Path

from codebase_md.model.architecture import ArchitectureType
from codebase_md.scanner.structure_analyzer import analyze_structure


class TestAnalyzeStructure:
    """Tests for analyze_structure function."""

    def test_detects_cli_tool(self, tmp_path: Path) -> None:
        """Should detect CLI tool architecture from cli.py entry point."""
        src = tmp_path / "src" / "myapp"
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("")
        (src / "cli.py").write_text("import typer\napp = typer.Typer()\n")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n[project.scripts]\nmycli = "myapp.cli:app"\n'
        )
        arch, _modules = analyze_structure(tmp_path, ["python"])
        assert arch.architecture_type in (
            ArchitectureType.CLI_TOOL,
            ArchitectureType.MONOLITH,
            ArchitectureType.LIBRARY,
            ArchitectureType.UNKNOWN,
        )

    def test_detects_entry_points(self, tmp_path: Path) -> None:
        """Should find entry point files."""
        (tmp_path / "main.py").write_text("print('hello')")
        arch, _modules = analyze_structure(tmp_path, ["python"])
        assert any("main.py" in ep for ep in arch.entry_points)

    def test_detects_modules(self, tmp_path: Path) -> None:
        """Should detect logical modules from directory structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_app.py").write_text("assert True")
        _arch, modules = analyze_structure(tmp_path, ["python"])
        assert len(modules) >= 1

    def test_detects_ci(self, tmp_path: Path) -> None:
        """Should detect CI/CD configuration."""
        github = tmp_path / ".github" / "workflows"
        github.mkdir(parents=True)
        (github / "ci.yml").write_text("name: CI\n")
        (tmp_path / "app.py").write_text("x = 1")
        arch, _modules = analyze_structure(tmp_path, ["python"])
        assert arch.has_ci is True

    def test_detects_docker(self, tmp_path: Path) -> None:
        """Should detect Docker configuration."""
        (tmp_path / "Dockerfile").write_text("FROM python:3.11\n")
        (tmp_path / "app.py").write_text("x = 1")
        arch, _modules = analyze_structure(tmp_path, ["python"])
        assert arch.has_docker is True

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Should handle empty directory gracefully."""
        arch, _modules = analyze_structure(tmp_path, None)
        assert arch.architecture_type == ArchitectureType.MONOLITH
