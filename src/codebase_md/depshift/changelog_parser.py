"""Changelog parser for extracting breaking changes and migration info.

Parses CHANGELOG.md, HISTORY.md, and similar files to identify
breaking changes, deprecations, and migration instructions between
two versions of a dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class ChangelogParseError(Exception):
    """Raised when changelog parsing fails."""


@dataclass(frozen=True)
class ChangelogEntry:
    """A single entry from a changelog.

    Attributes:
        version: The version this entry belongs to.
        category: Category — 'breaking', 'deprecated', 'added', 'fixed', 'changed', 'removed'.
        description: The changelog entry text.
        is_breaking: Whether this is a breaking change.
    """

    version: str
    category: str
    description: str
    is_breaking: bool = False


@dataclass(frozen=True)
class ChangelogSummary:
    """Summary of changes between two versions.

    Attributes:
        package_name: Name of the package.
        from_version: Starting version.
        to_version: Target version.
        entries: All changelog entries between the versions.
        breaking_changes: Entries flagged as breaking.
        deprecations: Entries flagged as deprecated.
        total_changes: Total number of entries.
    """

    package_name: str
    from_version: str
    to_version: str
    entries: list[ChangelogEntry] = field(default_factory=list)
    breaking_changes: list[ChangelogEntry] = field(default_factory=list)
    deprecations: list[ChangelogEntry] = field(default_factory=list)
    total_changes: int = 0


# Common changelog filenames
_CHANGELOG_NAMES: list[str] = [
    "CHANGELOG.md",
    "CHANGELOG",
    "CHANGES.md",
    "CHANGES",
    "HISTORY.md",
    "HISTORY",
    "NEWS.md",
    "NEWS",
    "RELEASES.md",
    "changelog.md",
    "changes.md",
    "history.md",
]

# Regex patterns for changelog parsing
_VERSION_HEADER_PATTERN = re.compile(
    r"^#{1,3}\s+\[?v?(\d+\.\d+(?:\.\d+)?)\]?"  # ## [1.2.3] or ## 1.2.3 or ### v1.2.3
    r"(?:\s*[-\u2013\u2014]\s*.*)?$",  # Optional date suffix (hyphen, en-dash, em-dash)
    re.MULTILINE,
)

_BREAKING_KEYWORDS = re.compile(
    r"\b(?:BREAKING|breaking\s+change|REMOVED|removed|backwards?\s*incompatible"
    r"|migrate|migration\s+required|no\s+longer\s+support)"
    r"\b",
    re.IGNORECASE,
)

_DEPRECATION_KEYWORDS = re.compile(
    r"\b(?:deprecated?|deprecating|will\s+be\s+removed|obsolete)\b",
    re.IGNORECASE,
)

_CATEGORY_HEADERS = re.compile(
    r"^#{2,4}\s+(added|changed|deprecated|removed|fixed|security|breaking\s*changes?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def find_changelog(project_path: Path) -> Path | None:
    """Find a changelog file in the given directory.

    Args:
        project_path: Directory to search in.

    Returns:
        Path to the changelog file, or None if not found.
    """
    for name in _CHANGELOG_NAMES:
        candidate = project_path / name
        if candidate.is_file():
            return candidate
    return None


def parse_changelog(
    content: str,
    package_name: str = "",
) -> list[ChangelogEntry]:
    """Parse changelog content into structured entries.

    Supports "Keep a Changelog" format and common variations.

    Args:
        content: Raw changelog text content.
        package_name: Name of the package (for context).

    Returns:
        List of ChangelogEntry instances.
    """
    entries: list[ChangelogEntry] = []
    current_version = "unknown"
    current_category = "changed"

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Check for version headers
        version_match = _VERSION_HEADER_PATTERN.match(stripped)
        if version_match:
            current_version = version_match.group(1)
            current_category = "changed"  # Reset category
            continue

        # Check for category headers (### Added, ### Breaking Changes, etc.)
        cat_match = _CATEGORY_HEADERS.match(stripped)
        if cat_match:
            raw_cat = cat_match.group(1).lower().strip()
            if "breaking" in raw_cat:
                current_category = "breaking"
            elif raw_cat in ("added", "changed", "deprecated", "removed", "fixed", "security"):
                current_category = raw_cat
            continue

        # Check for list items (changelog entries)
        if stripped.startswith(("-", "*", "•")):
            description = stripped.lstrip("-*• ").strip()
            if not description:
                continue

            # Determine if it's a breaking change
            is_breaking = (
                current_category == "breaking"
                or current_category == "removed"
                or bool(_BREAKING_KEYWORDS.search(description))
            )

            # Override category if keywords detected
            effective_category = current_category
            if is_breaking and effective_category not in ("breaking", "removed"):
                effective_category = "breaking"
            elif _DEPRECATION_KEYWORDS.search(description):
                effective_category = "deprecated"

            entries.append(
                ChangelogEntry(
                    version=current_version,
                    category=effective_category,
                    description=description,
                    is_breaking=is_breaking,
                )
            )

    return entries


def extract_changes_between(
    entries: list[ChangelogEntry],
    from_version: str,
    to_version: str,
    package_name: str = "",
) -> ChangelogSummary:
    """Extract changelog entries between two versions.

    Includes entries for all versions from from_version (exclusive)
    to to_version (inclusive).

    Args:
        entries: All parsed changelog entries.
        from_version: Current version (entries for this version excluded).
        to_version: Target version (entries for this version included).
        package_name: Name of the package.

    Returns:
        ChangelogSummary with filtered entries.
    """
    from codebase_md.depshift.version_differ import parse_version

    from_parts = parse_version(from_version)
    to_parts = parse_version(to_version)

    relevant: list[ChangelogEntry] = []
    for entry in entries:
        entry_parts = parse_version(entry.version)
        # Include if version is > from_version and <= to_version
        if _version_gt(entry_parts, from_parts) and _version_lte(entry_parts, to_parts):
            relevant.append(entry)

    breaking = [e for e in relevant if e.is_breaking]
    deprecations = [e for e in relevant if e.category == "deprecated"]

    return ChangelogSummary(
        package_name=package_name,
        from_version=from_version,
        to_version=to_version,
        entries=relevant,
        breaking_changes=breaking,
        deprecations=deprecations,
        total_changes=len(relevant),
    )


def _version_gt(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
) -> bool:
    """Check if version a is strictly greater than version b.

    Args:
        a: First version tuple (major, minor, patch).
        b: Second version tuple (major, minor, patch).

    Returns:
        True if a > b.
    """
    return a > b


def _version_lte(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
) -> bool:
    """Check if version a is less than or equal to version b.

    Args:
        a: First version tuple (major, minor, patch).
        b: Second version tuple (major, minor, patch).

    Returns:
        True if a <= b.
    """
    return a <= b
