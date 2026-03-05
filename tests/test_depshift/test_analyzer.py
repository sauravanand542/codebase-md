"""Tests for codebase_md.depshift.analyzer."""

from __future__ import annotations

from codebase_md.depshift.analyzer import HealthReport, HealthSummary, analyze_dependencies
from codebase_md.model.dependency import DependencyInfo


class TestAnalyzeDependencies:
    """Tests for analyze_dependencies function."""

    def test_offline_mode(self) -> None:
        """Should work in offline mode without network."""
        deps = [
            DependencyInfo(name="typer", version="0.9.0", ecosystem="pypi"),
            DependencyInfo(name="rich", version="13.0.0", ecosystem="pypi"),
        ]
        report = analyze_dependencies(deps, query_registries=False)
        assert isinstance(report, HealthReport)
        assert len(report.dependencies) == 2
        assert isinstance(report.summary, HealthSummary)

    def test_summary_counts(self) -> None:
        """Should produce correct summary counts."""
        deps = [
            DependencyInfo(name="a", version="1.0", ecosystem="pypi"),
            DependencyInfo(name="b", version="2.0", ecosystem="pypi"),
        ]
        report = analyze_dependencies(deps, query_registries=False)
        assert report.summary.total == 2

    def test_empty_deps(self) -> None:
        """Should handle empty dependency list."""
        report = analyze_dependencies([], query_registries=False)
        assert report.summary.total == 0
        assert report.dependencies == []

    def test_unknown_ecosystem(self) -> None:
        """Should handle unknown ecosystem gracefully."""
        deps = [
            DependencyInfo(name="mystery", version="1.0", ecosystem="unknown"),
        ]
        report = analyze_dependencies(deps, query_registries=False)
        assert len(report.dependencies) == 1


class TestHealthSummary:
    """Tests for HealthSummary model."""

    def test_default_values(self) -> None:
        """Should have zero defaults."""
        summary = HealthSummary()
        assert summary.total == 0
        assert summary.healthy == 0
        assert summary.average_score == 0.0
