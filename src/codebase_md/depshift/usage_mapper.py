"""Usage mapper — maps dependency APIs to code locations.

Scans source files to find where each dependency is imported and
used, producing a mapping of dependency name → list of file locations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class UsageMapperError(Exception):
    """Raised when usage mapping fails."""


@dataclass(frozen=True)
class UsageLocation:
    """A location where a dependency is used in the codebase.

    Attributes:
        file_path: Relative path to the source file.
        line_number: Line number where the import/usage occurs.
        line_content: The actual line of code.
        usage_type: Type of usage — 'import', 'from_import', or 'require'.
    """

    file_path: str
    line_number: int
    line_content: str
    usage_type: str = "import"


@dataclass
class DependencyUsageMap:
    """Mapping of a dependency to all its usage locations.

    Attributes:
        dependency_name: Name of the dependency (e.g. 'requests').
        ecosystem: Package ecosystem (e.g. 'pypi', 'npm').
        locations: List of file locations where this dep is used.
        import_count: Total number of imports across all files.
    """

    dependency_name: str
    ecosystem: str = "unknown"
    locations: list[UsageLocation] = field(default_factory=list)
    import_count: int = 0


# File extensions to scan per ecosystem
_ECOSYSTEM_EXTENSIONS: dict[str, set[str]] = {
    "pypi": {".py"},
    "npm": {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"},
}

# Default directories to skip
_DEFAULT_EXCLUDES: set[str] = {
    "node_modules", ".venv", "venv", "__pycache__", ".git",
    "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
    ".pytest_cache", "egg-info", ".eggs",
}


def map_dependency_usage(
    root_path: Path,
    dependency_names: list[str],
    ecosystem: str,
    *,
    exclude: set[str] | None = None,
) -> list[DependencyUsageMap]:
    """Map where each dependency is imported/used in the codebase.

    Scans source files matching the ecosystem's extensions and
    searches for import statements referencing each dependency.

    Args:
        root_path: Project root directory.
        dependency_names: List of dependency names to search for.
        ecosystem: Package ecosystem ('pypi' or 'npm').
        exclude: Directory names to skip.

    Returns:
        List of DependencyUsageMap, one per dependency.

    Raises:
        UsageMapperError: If root_path is invalid.
    """
    if not root_path.exists():
        raise UsageMapperError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise UsageMapperError(f"Path is not a directory: {root_path}")

    extensions = _ECOSYSTEM_EXTENSIONS.get(ecosystem, set())
    if not extensions:
        return [
            DependencyUsageMap(dependency_name=name, ecosystem=ecosystem)
            for name in dependency_names
        ]

    exclude_dirs = exclude if exclude is not None else _DEFAULT_EXCLUDES

    # Collect all source files
    source_files = _collect_source_files(root_path, extensions, exclude_dirs)

    # Build search patterns for each dependency
    dep_patterns = _build_patterns(dependency_names, ecosystem)

    # Scan files
    results: dict[str, DependencyUsageMap] = {
        name: DependencyUsageMap(dependency_name=name, ecosystem=ecosystem)
        for name in dependency_names
    }

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        relative_path = str(file_path.relative_to(root_path))

        for line_num, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue

            for dep_name, pattern, usage_type in dep_patterns:
                if pattern.search(stripped):
                    loc = UsageLocation(
                        file_path=relative_path,
                        line_number=line_num,
                        line_content=stripped,
                        usage_type=usage_type,
                    )
                    results[dep_name].locations.append(loc)
                    results[dep_name].import_count += 1

    return list(results.values())


def get_usage_file_paths(usage_map: DependencyUsageMap) -> list[str]:
    """Get unique file paths from a usage map.

    Args:
        usage_map: The dependency usage mapping.

    Returns:
        Sorted list of unique file paths where the dep is used.
    """
    return sorted({loc.file_path for loc in usage_map.locations})


def _collect_source_files(
    root_path: Path,
    extensions: set[str],
    exclude_dirs: set[str],
) -> list[Path]:
    """Collect all source files matching the given extensions.

    Args:
        root_path: Root directory to walk.
        extensions: File extensions to include (e.g. {'.py'}).
        exclude_dirs: Directory names to skip.

    Returns:
        List of matching file paths.
    """
    files: list[Path] = []

    for item in root_path.rglob("*"):
        # Skip excluded directories
        if any(part in exclude_dirs for part in item.parts):
            continue
        if item.is_file() and item.suffix in extensions:
            files.append(item)

    return files


def _build_patterns(
    dependency_names: list[str],
    ecosystem: str,
) -> list[tuple[str, re.Pattern[str], str]]:
    """Build regex patterns for detecting dependency imports.

    Args:
        dependency_names: Names of dependencies to search for.
        ecosystem: Package ecosystem.

    Returns:
        List of (dep_name, compiled_regex, usage_type) tuples.
    """
    patterns: list[tuple[str, re.Pattern[str], str]] = []

    for name in dependency_names:
        escaped = re.escape(name)
        # Normalize package name for Python (e.g., 'pyyaml' → 'yaml' import)
        import_name = _normalize_import_name(name, ecosystem)
        escaped_import = re.escape(import_name)

        if ecosystem == "pypi":
            # Match: import X, from X import ..., from X.submod import ...
            patterns.append((
                name,
                re.compile(rf'^import\s+{escaped_import}\b'),
                "import",
            ))
            patterns.append((
                name,
                re.compile(rf'^from\s+{escaped_import}\b'),
                "from_import",
            ))
            # Also match the original name if different
            if import_name != name:
                patterns.append((
                    name,
                    re.compile(rf'^import\s+{escaped}\b'),
                    "import",
                ))
                patterns.append((
                    name,
                    re.compile(rf'^from\s+{escaped}\b'),
                    "from_import",
                ))
        elif ecosystem == "npm":
            # Match: import ... from 'X', require('X'), import 'X'
            patterns.append((
                name,
                re.compile(rf"""(?:from\s+['"]|require\s*\(\s*['"]){escaped}(?:[/'"@])"""),
                "import",
            ))
            # Also match exact package name at end of string
            patterns.append((
                name,
                re.compile(rf"""(?:from\s+['"]|require\s*\(\s*['"]){escaped}['"]"""),
                "import",
            ))

    return patterns


# Common PyPI package name → import name mappings
_PYPI_IMPORT_NAMES: dict[str, str] = {
    "pyyaml": "yaml",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "python-dateutil": "dateutil",
    "beautifulsoup4": "bs4",
    "python-dotenv": "dotenv",
    "types-pyyaml": "yaml",
    "pytest-cov": "pytest_cov",
}


def _normalize_import_name(package_name: str, ecosystem: str) -> str:
    """Convert a package name to its likely import name.

    Args:
        package_name: The package name as listed in dependencies.
        ecosystem: The package ecosystem.

    Returns:
        The import name used in code.
    """
    if ecosystem == "pypi":
        lower_name = package_name.lower()
        if lower_name in _PYPI_IMPORT_NAMES:
            return _PYPI_IMPORT_NAMES[lower_name]
        # Replace hyphens with underscores (common convention)
        return lower_name.replace("-", "_")

    # npm packages are imported as-is
    return package_name
