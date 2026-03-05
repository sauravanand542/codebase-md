"""Tests for codebase_md.scanner.dependency_parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from codebase_md.scanner.dependency_parser import DependencyParseError, parse_dependencies


class TestParseDependencies:
    """Tests for parse_dependencies function."""

    def test_parses_pyproject_toml(self, tmp_path: Path) -> None:
        """Should parse dependencies from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\n"
            'name = "test"\n'
            "dependencies = [\n"
            '    "typer>=0.9.0",\n'
            '    "rich>=13.0.0",\n'
            '    "pydantic>=2.0.0",\n'
            "]\n"
        )
        deps = parse_dependencies(tmp_path)
        assert len(deps) >= 3
        names = [d.name for d in deps]
        assert "typer" in names
        assert "rich" in names

    def test_parses_requirements_txt(self, tmp_path: Path) -> None:
        """Should parse dependencies from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("flask==2.3.0\nrequests>=2.28.0\nnumpy\n")
        deps = parse_dependencies(tmp_path)
        assert len(deps) >= 3
        names = [d.name for d in deps]
        assert "flask" in names
        assert "requests" in names

    def test_parses_package_json(self, tmp_path: Path) -> None:
        """Should parse dependencies from package.json."""
        (tmp_path / "package.json").write_text(
            '{"name": "test", "dependencies": {"react": "^18.2.0", "next": "^14.0.0"}}'
        )
        deps = parse_dependencies(tmp_path)
        assert len(deps) >= 2
        names = [d.name for d in deps]
        assert "react" in names
        assert "next" in names

    def test_pypi_ecosystem(self, tmp_path: Path) -> None:
        """Should set ecosystem to pypi for Python deps."""
        (tmp_path / "requirements.txt").write_text("flask==2.3.0\n")
        deps = parse_dependencies(tmp_path)
        assert all(d.ecosystem == "pypi" for d in deps)

    def test_npm_ecosystem(self, tmp_path: Path) -> None:
        """Should set ecosystem to npm for JS deps."""
        (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.18.0"}}')
        deps = parse_dependencies(tmp_path)
        assert all(d.ecosystem == "npm" for d in deps)

    def test_no_deps_files(self, tmp_path: Path) -> None:
        """Should return empty list when no manifest files found."""
        deps = parse_dependencies(tmp_path)
        assert deps == []

    def test_nonexistent_path(self) -> None:
        """Should raise on nonexistent path."""
        with pytest.raises(DependencyParseError):
            parse_dependencies(Path("/nonexistent/path"))

    def test_deduplication(self, tmp_path: Path) -> None:
        """Should not return duplicate deps from multiple manifest files."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\n\ndependencies = [\n    "requests>=2.28.0",\n]\n'
        )
        (tmp_path / "requirements.txt").write_text("requests>=2.28.0\n")
        deps = parse_dependencies(tmp_path)
        names = [d.name for d in deps if d.name == "requests"]
        assert len(names) == 1
