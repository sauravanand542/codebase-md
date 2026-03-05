"""Core dependency health analyzer for DepShift.

Analyzes project dependencies by querying registries for latest
versions, calculating health scores based on staleness, deprecation,
and version gap, and enriching DependencyInfo with actionable data.
"""

from __future__ import annotations

import re

from codebase_md.depshift.registries.npm import (
    NpmRegistryError,
)
from codebase_md.depshift.registries.npm import (
    fetch_package_info_sync as npm_fetch_sync,
)
from codebase_md.depshift.registries.pypi import (
    PyPIRegistryError,
)
from codebase_md.depshift.registries.pypi import (
    fetch_package_info_sync as pypi_fetch_sync,
)
from codebase_md.depshift.version_differ import (
    VersionDiffResult,
    compare_versions,
)
from codebase_md.model.dependency import DependencyHealth, DependencyInfo


class DepShiftAnalyzerError(Exception):
    """Raised when dependency analysis fails."""


class HealthReport:
    """Full health report for all project dependencies.

    Attributes:
        dependencies: List of enriched DependencyInfo with health data.
        summary: Overall health summary statistics.
        warnings: Non-fatal issues encountered during analysis.
    """

    def __init__(
        self,
        dependencies: list[DependencyInfo],
        summary: HealthSummary,
        warnings: list[str],
    ) -> None:
        self.dependencies = dependencies
        self.summary = summary
        self.warnings = warnings


class HealthSummary:
    """Summary statistics for dependency health.

    Attributes:
        total: Total number of dependencies analyzed.
        healthy: Number of healthy (up-to-date) dependencies.
        outdated: Number of outdated dependencies.
        deprecated: Number of deprecated dependencies.
        unknown: Number with unknown status (registry query failed).
        average_score: Average health score across all deps.
    """

    def __init__(
        self,
        total: int = 0,
        healthy: int = 0,
        outdated: int = 0,
        deprecated: int = 0,
        unknown: int = 0,
        average_score: float = 0.0,
    ) -> None:
        self.total = total
        self.healthy = healthy
        self.outdated = outdated
        self.deprecated = deprecated
        self.unknown = unknown
        self.average_score = average_score


def analyze_dependencies(
    dependencies: list[DependencyInfo],
    *,
    query_registries: bool = True,
    timeout: float = 10.0,
) -> HealthReport:
    """Analyze all dependencies and produce a health report.

    For each dependency, queries the appropriate registry for the
    latest version, calculates a health score, and determines
    the health status.

    Args:
        dependencies: List of DependencyInfo from the scanner.
        query_registries: Whether to query npm/PyPI for latest versions.
        timeout: HTTP timeout for registry queries.

    Returns:
        HealthReport with enriched dependencies and summary.
    """
    enriched: list[DependencyInfo] = []
    warnings: list[str] = []

    for dep in dependencies:
        try:
            enriched_dep = _analyze_single(dep, query_registries=query_registries, timeout=timeout)
            enriched.append(enriched_dep)
        except DepShiftAnalyzerError as e:
            warnings.append(str(e))
            enriched.append(dep)

    summary = _compute_summary(enriched)
    return HealthReport(dependencies=enriched, summary=summary, warnings=warnings)


def analyze_single_dependency(
    dep: DependencyInfo,
    *,
    query_registries: bool = True,
    timeout: float = 10.0,
) -> DependencyInfo:
    """Analyze a single dependency and return enriched info.

    Args:
        dep: The dependency to analyze.
        query_registries: Whether to query the registry.
        timeout: HTTP timeout for registry queries.

    Returns:
        Enriched DependencyInfo with health data.

    Raises:
        DepShiftAnalyzerError: If analysis fails critically.
    """
    return _analyze_single(dep, query_registries=query_registries, timeout=timeout)


def _analyze_single(
    dep: DependencyInfo,
    *,
    query_registries: bool = True,
    timeout: float = 10.0,
) -> DependencyInfo:
    """Analyze a single dependency with registry lookup.

    Args:
        dep: The DependencyInfo to enrich.
        query_registries: Whether to query the registry.
        timeout: HTTP timeout.

    Returns:
        Enriched DependencyInfo.

    Raises:
        DepShiftAnalyzerError: On critical failure.
    """
    latest_version: str | None = dep.latest
    health = dep.health
    health_score = dep.health_score
    deprecated = False

    if query_registries:
        try:
            if dep.ecosystem == "pypi":
                pkg_info = pypi_fetch_sync(dep.name, timeout=timeout)
                latest_version = pkg_info.latest_version
            elif dep.ecosystem == "npm":
                npm_info = npm_fetch_sync(dep.name, timeout=timeout)
                latest_version = npm_info.latest_version
                if npm_info.deprecated:
                    deprecated = True
            else:
                # Unsupported ecosystem — keep existing data
                return dep
        except (PyPIRegistryError, NpmRegistryError) as e:
            raise DepShiftAnalyzerError(
                f"Registry query failed for '{dep.name}' ({dep.ecosystem}): {e}"
            ) from e

    # Calculate health based on version comparison
    if latest_version:
        current_clean = clean_version(dep.version)
        latest_clean = clean_version(latest_version)

        if deprecated:
            health = DependencyHealth.DEPRECATED
            health_score = 0.1
        elif current_clean == latest_clean:
            health = DependencyHealth.HEALTHY
            health_score = 1.0
        else:
            diff = compare_versions(current_clean, latest_clean)
            health, health_score = _score_from_diff(diff)
    else:
        health = DependencyHealth.UNKNOWN
        health_score = 0.5

    return DependencyInfo(
        name=dep.name,
        version=dep.version,
        latest=latest_version,
        health=health,
        health_score=health_score,
        usage_locations=dep.usage_locations,
        breaking_changes=dep.breaking_changes,
        ecosystem=dep.ecosystem,
    )


def clean_version(version: str) -> str:
    """Clean a version string by stripping operators and whitespace.

    Extracts the first version number from constraints like
    '>=1.2.0', '~1.0', '^2.3.4', '==1.5.0'.

    Args:
        version: Raw version string from a manifest.

    Returns:
        Clean version number (e.g. '1.2.0').
    """
    # Remove common prefixes/operators
    cleaned = re.sub(r'^[~^>=<!]+\s*', '', version.strip())
    # Take only the first version if comma-separated
    cleaned = cleaned.split(",")[0].strip()
    # Remove any remaining operators
    cleaned = re.sub(r'^[>=<!]+\s*', '', cleaned)
    # Remove trailing wildcards
    cleaned = cleaned.rstrip(".*")
    return cleaned or version


def _score_from_diff(diff: VersionDiffResult) -> tuple[DependencyHealth, float]:
    """Calculate health status and score from a version diff.

    Scoring logic:
    - Same version: 1.0 (healthy)
    - Patch behind: 0.8 (healthy)
    - Minor behind: 0.5 (outdated)
    - Major behind: 0.2 (outdated, likely breaking)

    Args:
        diff: The version comparison result.

    Returns:
        Tuple of (DependencyHealth status, score float).
    """
    if diff.major_diff > 0:
        # Multiple major versions behind — likely breaking changes
        score = max(0.1, 0.3 - (diff.major_diff - 1) * 0.1)
        return DependencyHealth.OUTDATED, round(score, 2)
    elif diff.minor_diff > 0:
        # Minor versions behind — may have new features, usually compatible
        score = max(0.3, 0.7 - diff.minor_diff * 0.05)
        return DependencyHealth.OUTDATED, round(score, 2)
    elif diff.patch_diff > 0:
        # Patch versions behind — bug fixes, should be safe to update
        score = max(0.6, 0.9 - diff.patch_diff * 0.02)
        return DependencyHealth.HEALTHY, round(score, 2)
    else:
        # Same or newer
        return DependencyHealth.HEALTHY, 1.0


def _compute_summary(dependencies: list[DependencyInfo]) -> HealthSummary:
    """Compute summary statistics from analyzed dependencies.

    Args:
        dependencies: List of enriched DependencyInfo.

    Returns:
        HealthSummary with counts and average score.
    """
    total = len(dependencies)
    if total == 0:
        return HealthSummary()

    healthy = sum(1 for d in dependencies if d.health == DependencyHealth.HEALTHY)
    outdated = sum(1 for d in dependencies if d.health == DependencyHealth.OUTDATED)
    deprecated = sum(1 for d in dependencies if d.health == DependencyHealth.DEPRECATED)
    unknown = sum(1 for d in dependencies if d.health == DependencyHealth.UNKNOWN)
    avg_score = sum(d.health_score for d in dependencies) / total

    return HealthSummary(
        total=total,
        healthy=healthy,
        outdated=outdated,
        deprecated=deprecated,
        unknown=unknown,
        average_score=round(avg_score, 2),
    )
