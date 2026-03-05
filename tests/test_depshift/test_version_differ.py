"""Tests for codebase_md.depshift.version_differ."""

from __future__ import annotations

from codebase_md.depshift.version_differ import (
    VersionDiffResult,
    compare_versions,
    format_version_diff,
)


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_same_version(self) -> None:
        """Should report no diff for identical versions."""
        result = compare_versions("1.2.3", "1.2.3")
        assert result.is_behind is False
        assert result.upgrade_type == "none"
        assert result.major_diff == 0

    def test_patch_behind(self) -> None:
        """Should detect patch-level difference."""
        result = compare_versions("1.2.3", "1.2.5")
        assert result.is_behind is True
        assert result.upgrade_type == "patch"
        assert result.patch_diff == 2
        assert result.breaking_likely is False

    def test_minor_behind(self) -> None:
        """Should detect minor-level difference."""
        result = compare_versions("1.2.3", "1.5.0")
        assert result.is_behind is True
        assert result.upgrade_type == "minor"
        assert result.minor_diff == 3

    def test_major_behind(self) -> None:
        """Should detect major-level difference with breaking flag."""
        result = compare_versions("1.2.3", "3.0.0")
        assert result.is_behind is True
        assert result.upgrade_type == "major"
        assert result.major_diff == 2
        assert result.breaking_likely is True

    def test_handles_two_part_version(self) -> None:
        """Should handle versions like '2.0'."""
        result = compare_versions("1.0", "2.0")
        assert result.is_behind is True
        assert result.upgrade_type == "major"

    def test_handles_single_part_version(self) -> None:
        """Should handle versions like '3'."""
        result = compare_versions("2", "3")
        assert result.is_behind is True
        assert result.upgrade_type == "major"

    def test_handles_prerelease_suffix(self) -> None:
        """Should strip pre-release suffixes for comparison."""
        result = compare_versions("1.0.0-beta", "1.0.0")
        # Should handle gracefully (not crash)
        assert isinstance(result, VersionDiffResult)


class TestFormatVersionDiff:
    """Tests for format_version_diff function."""

    def test_formats_same_version(self) -> None:
        """Should indicate up-to-date."""
        result = compare_versions("1.0.0", "1.0.0")
        output = format_version_diff(result)
        assert "1.0.0" in output

    def test_formats_behind_version(self) -> None:
        """Should show current → latest."""
        result = compare_versions("1.0.0", "2.0.0")
        output = format_version_diff(result)
        assert "1.0.0" in output
        assert "2.0.0" in output
