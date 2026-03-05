"""Version comparison and diffing for dependency analysis.

Compares semantic versions to determine the gap between current
and latest, identify breaking change likelihood, and calculate
upgrade effort.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class VersionDiffError(Exception):
    """Raised when version comparison fails."""


@dataclass(frozen=True)
class VersionDiffResult:
    """Result of comparing two semantic versions.

    Attributes:
        current: The current (installed) version string.
        latest: The latest (available) version string.
        major_diff: Number of major versions behind (0 = same major).
        minor_diff: Number of minor versions behind (0 = same minor).
        patch_diff: Number of patch versions behind (0 = same patch).
        is_behind: Whether current is behind latest.
        upgrade_type: 'major', 'minor', 'patch', or 'none'.
        breaking_likely: Whether breaking changes are likely (major bump).
    """

    current: str
    latest: str
    major_diff: int = 0
    minor_diff: int = 0
    patch_diff: int = 0
    is_behind: bool = False
    upgrade_type: str = "none"
    breaking_likely: bool = False


def compare_versions(current: str, latest: str) -> VersionDiffResult:
    """Compare two semantic version strings and compute the diff.

    Handles versions like '1.2.3', '2.0', '3', and pre-release
    suffixes (which are stripped for comparison).

    Args:
        current: Current version string (e.g. '1.2.3').
        latest: Latest version string (e.g. '2.0.0').

    Returns:
        VersionDiffResult with the gap analysis.
    """
    cur_parts = _parse_version(current)
    lat_parts = _parse_version(latest)

    major_diff = max(0, lat_parts[0] - cur_parts[0])
    minor_diff = max(0, lat_parts[1] - cur_parts[1]) if major_diff == 0 else 0
    patch_diff = (
        max(0, lat_parts[2] - cur_parts[2])
        if major_diff == 0 and minor_diff == 0
        else 0
    )

    is_behind = (
        cur_parts[0] < lat_parts[0]
        or (cur_parts[0] == lat_parts[0] and cur_parts[1] < lat_parts[1])
        or (
            cur_parts[0] == lat_parts[0]
            and cur_parts[1] == lat_parts[1]
            and cur_parts[2] < lat_parts[2]
        )
    )

    if major_diff > 0:
        upgrade_type = "major"
    elif minor_diff > 0:
        upgrade_type = "minor"
    elif patch_diff > 0:
        upgrade_type = "patch"
    else:
        upgrade_type = "none"

    breaking_likely = major_diff > 0

    return VersionDiffResult(
        current=current,
        latest=latest,
        major_diff=major_diff,
        minor_diff=minor_diff,
        patch_diff=patch_diff,
        is_behind=is_behind,
        upgrade_type=upgrade_type,
        breaking_likely=breaking_likely,
    )


def _parse_version(version: str) -> tuple[int, int, int]:
    """Parse a version string into (major, minor, patch) tuple.

    Handles various formats:
    - '1.2.3' → (1, 2, 3)
    - '2.0' → (2, 0, 0)
    - '3' → (3, 0, 0)
    - '1.2.3-beta.1' → (1, 2, 3)
    - '1.2.3rc1' → (1, 2, 3)

    Args:
        version: Version string to parse.

    Returns:
        Tuple of (major, minor, patch) integers.
    """
    # Strip pre-release suffixes
    cleaned = re.split(r'[-+a-zA-Z]', version.strip())[0]

    parts = cleaned.split(".")
    try:
        major = int(parts[0]) if len(parts) > 0 and parts[0] else 0
        minor = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        patch = int(parts[2]) if len(parts) > 2 and parts[2] else 0
    except ValueError:
        major, minor, patch = 0, 0, 0

    return major, minor, patch


def format_version_diff(diff: VersionDiffResult) -> str:
    """Format a version diff result as a human-readable string.

    Args:
        diff: The VersionDiffResult to format.

    Returns:
        Human-readable description of the version gap.
    """
    if not diff.is_behind:
        return f"{diff.current} — up to date"

    parts: list[str] = [f"{diff.current} → {diff.latest}"]

    if diff.upgrade_type == "major":
        parts.append(f"{diff.major_diff} major version(s) behind")
        parts.append("⚠ breaking changes likely")
    elif diff.upgrade_type == "minor":
        parts.append(f"{diff.minor_diff} minor version(s) behind")
    elif diff.upgrade_type == "patch":
        parts.append(f"{diff.patch_diff} patch version(s) behind")

    return " — ".join(parts)
