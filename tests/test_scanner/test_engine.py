"""Tests for codebase_md.scanner.engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from codebase_md.scanner.engine import ScannerError, scan_project


class TestScanProject:
    """Tests for scan_project function."""

    def test_scans_python_project(self, sample_python_project: Path) -> None:
        """Should scan a Python project and return a ProjectModel."""
        result = scan_project(sample_python_project, persist=False)
        assert result.model.name is not None
        assert result.duration >= 0

    def test_detects_languages(self, sample_python_project: Path) -> None:
        """Should detect Python as a language."""
        result = scan_project(sample_python_project, persist=False)
        assert "python" in result.model.languages

    def test_detects_dependencies(self, sample_python_project: Path) -> None:
        """Should parse dependencies from pyproject.toml."""
        result = scan_project(sample_python_project, persist=False)
        dep_names = [d.name for d in result.model.dependencies]
        assert "typer" in dep_names
        assert "rich" in dep_names

    def test_persist_creates_project_json(self, sample_python_project: Path) -> None:
        """Should persist project.json when persist=True."""
        # Initialize .codebase/ first
        codebase_dir = sample_python_project / ".codebase"
        codebase_dir.mkdir(exist_ok=True)

        import yaml

        config = {"version": 1, "generators": ["claude"]}
        (codebase_dir / "config.yaml").write_text(
            yaml.dump(config), encoding="utf-8"
        )

        scan_project(sample_python_project, persist=True)
        project_json = codebase_dir / "project.json"
        assert project_json.is_file()

    def test_nonexistent_path(self) -> None:
        """Should raise ScannerError for nonexistent path."""
        with pytest.raises(ScannerError):
            scan_project(Path("/nonexistent/project"))

    def test_not_a_directory(self, tmp_path: Path) -> None:
        """Should raise ScannerError for file path."""
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(ScannerError):
            scan_project(f)

    def test_empty_project(self, tmp_path: Path) -> None:
        """Should handle empty project gracefully."""
        result = scan_project(tmp_path, persist=False)
        assert result.model.name is not None
        assert result.model.languages == [] or isinstance(result.model.languages, list)
