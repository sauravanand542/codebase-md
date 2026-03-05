"""Dependency parsing for codebase scanning.

Reads package manifest files (package.json, requirements.txt,
pyproject.toml, go.mod, Cargo.toml) and extracts dependency
information including names, version constraints, and ecosystem.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from codebase_md.model.dependency import DependencyInfo


class DependencyParseError(Exception):
    """Raised when dependency parsing fails."""


def parse_dependencies(root_path: Path) -> list[DependencyInfo]:
    """Parse all dependency files found in the project root.

    Scans for known dependency manifest files and extracts dependency
    info from each one found.

    Args:
        root_path: Root directory of the project to scan.

    Returns:
        List of DependencyInfo instances from all parseable manifests.

    Raises:
        DependencyParseError: If root_path does not exist or is not a directory.
    """
    if not root_path.exists():
        raise DependencyParseError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise DependencyParseError(f"Path is not a directory: {root_path}")

    all_deps: list[DependencyInfo] = []
    seen_names: set[str] = set()

    # Try each parser in order
    parsers: list[tuple[str, Callable[[Path], list[DependencyInfo]]]] = [
        ("package.json", _parse_package_json),
        ("requirements.txt", _parse_requirements_txt),
        ("pyproject.toml", _parse_pyproject_toml),
        ("go.mod", _parse_go_mod),
        ("Cargo.toml", _parse_cargo_toml),
        ("Gemfile", _parse_gemfile),
    ]

    for filename, parser_fn in parsers:
        manifest_path = root_path / filename
        if manifest_path.is_file():
            try:
                deps = parser_fn(manifest_path)
                for dep in deps:
                    # Avoid duplicates across different manifest files
                    key = f"{dep.ecosystem}:{dep.name}"
                    if key not in seen_names:
                        seen_names.add(key)
                        all_deps.append(dep)
            except DependencyParseError:
                # Log but continue with other parsers
                continue

    return all_deps


def _parse_package_json(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from package.json.

    Extracts both dependencies and devDependencies.

    Args:
        path: Path to package.json file.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read or parsed.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DependencyParseError(f"Invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []

    for section in ("dependencies", "devDependencies", "peerDependencies"):
        section_deps = data.get(section, {})
        if not isinstance(section_deps, dict):
            continue
        for name, version in section_deps.items():
            version_str = str(version) if version else "*"
            deps.append(
                DependencyInfo(
                    name=name,
                    version=version_str,
                    ecosystem="npm",
                )
            )

    return deps


def _parse_requirements_txt(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from requirements.txt.

    Handles version specifiers, comments, and blank lines.

    Args:
        path: Path to requirements.txt file.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []
    req_pattern = re.compile(
        r"^([a-zA-Z0-9_][a-zA-Z0-9._-]*)\s*"  # package name
        r"(?:\[.*?\])?\s*"  # optional extras
        r"([><=!~]+\s*[\d.]+(?:\s*,\s*[><=!~]+\s*[\d.]+)*)?"  # version spec
    )

    for line in content.splitlines():
        line = line.strip()
        # Skip comments, blank lines, and flags
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        match = req_pattern.match(line)
        if match:
            name = match.group(1)
            version = match.group(2) or "*"
            deps.append(
                DependencyInfo(
                    name=name,
                    version=version.strip(),
                    ecosystem="pypi",
                )
            )

    return deps


def _parse_pyproject_toml(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from pyproject.toml.

    Extracts from [project.dependencies] and [project.optional-dependencies].

    Args:
        path: Path to pyproject.toml file.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read or parsed.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []

    # Parse dependencies using simple regex
    # Matches lines like: "package>=1.0.0",
    dep_pattern = re.compile(
        r'"([a-zA-Z0-9_][a-zA-Z0-9._-]*)'  # package name inside quotes
        r"(?:\[.*?\])?"  # optional extras
        r'\s*([><=!~]+\s*[\d.]+[^"]*)?'  # version spec
        r'"'
    )

    # Find the dependencies section
    in_deps_section = False
    in_optional_deps = False
    bracket_depth = 0

    for line in content.splitlines():
        stripped = line.strip()

        if stripped == "[project]":
            continue

        if stripped.startswith("dependencies") and "=" in stripped:
            in_deps_section = True
            bracket_depth = stripped.count("[") - stripped.count("]")
            continue

        if stripped.startswith("[project.optional-dependencies]"):
            in_optional_deps = True
            continue

        if (
            stripped.startswith("[")
            and not stripped.startswith("[[")
            and "=" not in stripped
            and not stripped.startswith("[project")
        ):
            in_deps_section = False
            in_optional_deps = False
            continue

        if in_deps_section or in_optional_deps:
            bracket_depth += stripped.count("[") - stripped.count("]")
            match = dep_pattern.search(line)
            if match:
                name = match.group(1)
                version = match.group(2) or "*"
                deps.append(
                    DependencyInfo(
                        name=name,
                        version=version.strip(),
                        ecosystem="pypi",
                    )
                )

            if bracket_depth <= 0 and in_deps_section:
                in_deps_section = False

    return deps


def _parse_go_mod(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from go.mod.

    Args:
        path: Path to go.mod file.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []
    in_require = False

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("require ("):
            in_require = True
            continue

        if stripped == ")" and in_require:
            in_require = False
            continue

        if in_require:
            parts = stripped.split()
            if len(parts) >= 2:
                deps.append(
                    DependencyInfo(
                        name=parts[0],
                        version=parts[1],
                        ecosystem="go",
                    )
                )
        elif stripped.startswith("require "):
            parts = stripped.replace("require ", "").split()
            if len(parts) >= 2:
                deps.append(
                    DependencyInfo(
                        name=parts[0],
                        version=parts[1],
                        ecosystem="go",
                    )
                )

    return deps


def _parse_cargo_toml(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from Cargo.toml.

    Args:
        path: Path to Cargo.toml file.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []
    in_deps_section = False

    # Simple TOML parsing for [dependencies] section
    dep_simple = re.compile(r'^([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"')
    dep_table = re.compile(r'^([a-zA-Z0-9_-]+)\s*=\s*\{.*?version\s*=\s*"([^"]+)"')

    for line in content.splitlines():
        stripped = line.strip()

        if stripped in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]"):
            in_deps_section = True
            continue
        if stripped.startswith("[") and in_deps_section and "dependencies" not in stripped:
            # New section — stop parsing deps
            in_deps_section = False
            continue

        if in_deps_section:
            match = dep_simple.match(stripped) or dep_table.match(stripped)
            if match:
                deps.append(
                    DependencyInfo(
                        name=match.group(1),
                        version=match.group(2),
                        ecosystem="cargo",
                    )
                )

    return deps


def _parse_gemfile(path: Path) -> list[DependencyInfo]:
    """Parse dependencies from Gemfile.

    Args:
        path: Path to Gemfile.

    Returns:
        List of DependencyInfo instances.

    Raises:
        DependencyParseError: If the file cannot be read.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise DependencyParseError(f"Cannot read {path}: {e}") from e

    deps: list[DependencyInfo] = []
    gem_pattern = re.compile(r"""gem\s+['"]([a-zA-Z0-9_-]+)['"]\s*(?:,\s*['"]([^'"]+)['"])?""")

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        match = gem_pattern.search(stripped)
        if match:
            deps.append(
                DependencyInfo(
                    name=match.group(1),
                    version=match.group(2) or "*",
                    ecosystem="rubygems",
                )
            )

    return deps
