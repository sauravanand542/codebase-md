"""Tests for codebase_md.scanner.language_detector."""

from __future__ import annotations

from pathlib import Path

import pytest

from codebase_md.scanner.language_detector import (
    EXTENSION_MAP,
    LanguageDetectionError,
    detect_frameworks,
    detect_languages,
)


class TestDetectLanguages:
    """Tests for detect_languages function."""

    def test_detects_python_files(self, tmp_path: Path) -> None:
        """Should detect .py files as Python."""
        (tmp_path / "app.py").write_text("print('hello')")
        (tmp_path / "utils.py").write_text("x = 1")
        result = detect_languages(tmp_path)
        assert "python" in result

    def test_detects_multiple_languages(self, tmp_path: Path) -> None:
        """Should detect multiple languages."""
        (tmp_path / "app.py").write_text("x = 1")
        (tmp_path / "index.ts").write_text("const x = 1;")
        result = detect_languages(tmp_path)
        assert "python" in result
        assert "typescript" in result

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Should return empty list for empty directory."""
        result = detect_languages(tmp_path)
        assert result == []

    def test_excludes_directories(self, tmp_path: Path) -> None:
        """Should skip excluded directories."""
        node_modules = tmp_path / "node_modules" / "pkg"
        node_modules.mkdir(parents=True)
        (node_modules / "index.js").write_text("module.exports = {}")
        (tmp_path / "app.py").write_text("x = 1")
        result = detect_languages(tmp_path)
        # node_modules should be excluded, so only python
        assert "python" in result

    def test_nonexistent_path(self) -> None:
        """Should raise on nonexistent path."""
        with pytest.raises(LanguageDetectionError):
            detect_languages(Path("/nonexistent/path"))

    def test_extension_map_completeness(self) -> None:
        """Should have common extensions mapped."""
        assert ".py" in EXTENSION_MAP
        assert ".js" in EXTENSION_MAP
        assert ".ts" in EXTENSION_MAP
        assert ".go" in EXTENSION_MAP
        assert ".rs" in EXTENSION_MAP


class TestDetectFrameworks:
    """Tests for detect_frameworks function."""

    def test_detects_python_framework_from_pyproject(self, tmp_path: Path) -> None:
        """Should detect Python frameworks from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["fastapi"]\n'
        )
        frameworks = detect_frameworks(tmp_path)
        assert any("fastapi" in str(f).lower() for f in frameworks)

    def test_no_frameworks_in_empty_dir(self, tmp_path: Path) -> None:
        """Should return empty list when no framework markers found."""
        frameworks = detect_frameworks(tmp_path)
        assert frameworks == [] or len(frameworks) == 0
