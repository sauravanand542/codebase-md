"""Structure analysis for codebase scanning.

Analyzes the folder hierarchy to detect architecture patterns
(monolith, monorepo, microservice, library, CLI tool), identify
entry points, services, and logical modules.
"""

from __future__ import annotations

from pathlib import Path

from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType, ServiceInfo
from codebase_md.model.module import FileInfo, ModuleInfo
from codebase_md.scanner.language_detector import (
    _NON_CODE_LANGUAGES,
    DEFAULT_EXCLUDES,
    EXTENSION_MAP,
    _should_exclude,
)


class StructureAnalysisError(Exception):
    """Raised when structure analysis fails."""


# Patterns that suggest a monorepo
MONOREPO_MARKERS: list[str] = [
    "packages",
    "apps",
    "services",
    "libs",
    "modules",
]

# Well-known entry point filenames
ENTRY_POINT_NAMES: list[str] = [
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.ts",
    "index.js",
    "index.tsx",
    "index.jsx",
    "main.ts",
    "main.js",
    "main.go",
    "main.rs",
    "lib.rs",
    "Main.java",
    "App.java",
    "Program.cs",
    "server.ts",
    "server.js",
    "server.py",
    "cli.py",
    "cli.ts",
    "cli.js",
]

# Directories that indicate frontend
FRONTEND_INDICATORS: set[str] = {
    "frontend",
    "client",
    "web",
    "ui",
    "app",
    "pages",
    "components",
    "public",
    "static",
}

# Directories that indicate backend
BACKEND_INDICATORS: set[str] = {
    "backend",
    "server",
    "api",
    "services",
    "handlers",
    "controllers",
    "routes",
    "views",
    "endpoints",
}

# Files that indicate database usage
DATABASE_INDICATORS: list[str] = [
    "models.py",
    "schema.py",
    "migrations",
    "prisma",
    "drizzle",
    "schema.prisma",
    "alembic.ini",
    "knexfile.js",
    "knexfile.ts",
    "ormconfig.ts",
    "ormconfig.js",
    "database.py",
    "db.py",
]

# Docker indicators
DOCKER_INDICATORS: list[str] = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
]

# CI/CD indicators
CI_INDICATORS: list[str] = [
    ".github/workflows",
    ".gitlab-ci.yml",
    ".circleci",
    "Jenkinsfile",
    ".travis.yml",
    "bitbucket-pipelines.yml",
    "azure-pipelines.yml",
    ".buildkite",
]


def analyze_structure(
    root_path: Path,
    exclude: list[str] | None = None,
) -> tuple[ArchitectureInfo, list[ModuleInfo]]:
    """Analyze the project structure to detect architecture and modules.

    Examines the folder hierarchy, looks for marker files, and infers
    the architecture type, entry points, and logical module boundaries.

    Args:
        root_path: Root directory of the project to analyze.
        exclude: Directory/file names to skip. Uses DEFAULT_EXCLUDES if None.

    Returns:
        Tuple of (ArchitectureInfo, list of ModuleInfo).

    Raises:
        StructureAnalysisError: If root_path does not exist or is not a directory.
    """
    if not root_path.exists():
        raise StructureAnalysisError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise StructureAnalysisError(f"Path is not a directory: {root_path}")

    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES

    # Detect architecture type
    arch_type = _detect_architecture_type(root_path, exclude_list)

    # Find entry points
    entry_points = _find_entry_points(root_path, exclude_list)

    # Detect services (for monorepo/microservice)
    services = (
        _detect_services(root_path, exclude_list)
        if arch_type
        in {
            ArchitectureType.MONOREPO,
            ArchitectureType.MICROSERVICE,
        }
        else []
    )

    # Detect infrastructure markers
    has_frontend = _has_indicator(root_path, FRONTEND_INDICATORS, exclude_list)
    has_backend = _has_indicator(root_path, BACKEND_INDICATORS, exclude_list)
    has_database = _has_file_indicator(root_path, DATABASE_INDICATORS, exclude_list)
    has_docker = _has_file_indicator(root_path, DOCKER_INDICATORS, exclude_list)
    has_ci = _has_file_indicator(root_path, CI_INDICATORS, exclude_list)

    architecture = ArchitectureInfo(
        architecture_type=arch_type,
        entry_points=entry_points,
        services=services,
        has_frontend=has_frontend,
        has_backend=has_backend,
        has_database=has_database,
        has_docker=has_docker,
        has_ci=has_ci,
    )

    # Build module list
    modules = _detect_modules(root_path, exclude_list)

    return architecture, modules


def _detect_architecture_type(root_path: Path, exclude: list[str]) -> ArchitectureType:
    """Detect the architecture type from the directory structure.

    Args:
        root_path: Root directory of the project.
        exclude: Directory names to skip.

    Returns:
        The detected ArchitectureType.
    """
    top_level_dirs = [
        d.name
        for d in root_path.iterdir()
        if d.is_dir() and not _should_exclude(d.relative_to(root_path), exclude)
    ]

    # Check for monorepo markers
    monorepo_dirs = [d for d in top_level_dirs if d in MONOREPO_MARKERS]
    if monorepo_dirs:
        # Verify they actually contain sub-projects (have their own package files)
        for mono_dir in monorepo_dirs:
            mono_path = root_path / mono_dir
            sub_dirs = [d for d in mono_path.iterdir() if d.is_dir()]
            for sub_dir in sub_dirs:
                if _has_package_file(sub_dir):
                    return ArchitectureType.MONOREPO

    # Check for workspace config (another monorepo indicator)
    if _is_workspace_root(root_path):
        return ArchitectureType.MONOREPO

    # Check for generic monorepo pattern: multiple top-level dirs each with
    # their own package manifest (e.g. backend/ + frontend/, server/ + client/)
    top_dirs_with_packages = [
        d
        for d in top_level_dirs
        if _has_package_file(root_path / d)
    ]
    if len(top_dirs_with_packages) >= 2:
        return ArchitectureType.MONOREPO

    # Check for microservice indicators (multiple Dockerfiles or docker-compose with services)
    dockerfile_count = sum(
        1
        for _ in root_path.rglob("Dockerfile")
        if not _should_exclude(_.relative_to(root_path), exclude)
    )
    if dockerfile_count > 2:
        return ArchitectureType.MICROSERVICE

    # Check if it's a library
    if _is_library(root_path):
        return ArchitectureType.LIBRARY

    # Check if it's a CLI tool
    if _is_cli_tool(root_path):
        return ArchitectureType.CLI_TOOL

    # Default: monolith
    return ArchitectureType.MONOLITH


def _has_package_file(directory: Path) -> bool:
    """Check if a directory contains a package manifest file.

    Args:
        directory: Directory to check.

    Returns:
        True if a package file is found.
    """
    package_files = [
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "Gemfile",
        "pom.xml",
        "build.gradle",
    ]
    return any((directory / f).is_file() for f in package_files)


def _is_workspace_root(root_path: Path) -> bool:
    """Check if the project root is a workspace (npm, pnpm, yarn, etc.).

    Args:
        root_path: Root directory to check.

    Returns:
        True if workspace configuration is detected.
    """
    import json

    package_json = root_path / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if "workspaces" in data:
                return True
        except (json.JSONDecodeError, OSError):
            pass

    # pnpm workspaces
    if (root_path / "pnpm-workspace.yaml").is_file():
        return True

    # Lerna
    if (root_path / "lerna.json").is_file():
        return True

    # Nx
    if (root_path / "nx.json").is_file():
        return True

    # Turborepo
    return bool((root_path / "turbo.json").is_file())


def _is_library(root_path: Path) -> bool:
    """Check if the project appears to be a library/package.

    Args:
        root_path: Root directory to check.

    Returns:
        True if the project looks like a library.
    """
    # Python library indicators
    if (root_path / "setup.py").is_file() or (root_path / "setup.cfg").is_file():
        return True

    pyproject = root_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
            if (
                ("hatchling" in content or "setuptools" in content or "flit" in content)
                and "[project.scripts]" not in content
                and "[tool.poetry.scripts]" not in content
            ):
                return True
        except OSError:
            pass

    # Rust library
    return (root_path / "Cargo.toml").is_file() and (root_path / "src" / "lib.rs").is_file()


def _is_cli_tool(root_path: Path) -> bool:
    """Check if the project appears to be a CLI tool.

    Args:
        root_path: Root directory to check.

    Returns:
        True if the project looks like a CLI tool.
    """
    pyproject = root_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
            if "[project.scripts]" in content or "[tool.poetry.scripts]" in content:
                return True
        except OSError:
            pass

    # Check for bin field in package.json
    import json

    package_json = root_path / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if "bin" in data:
                return True
        except (json.JSONDecodeError, OSError):
            pass

    # Rust binary
    return (root_path / "Cargo.toml").is_file() and (root_path / "src" / "main.rs").is_file()


def _find_entry_points(root_path: Path, exclude: list[str]) -> list[str]:
    """Find main entry point files in the project.

    Args:
        root_path: Root directory of the project.
        exclude: Directory names to skip.

    Returns:
        List of relative paths to entry point files.
    """
    entry_points: list[str] = []

    for file_path in root_path.rglob("*"):
        try:
            if not file_path.is_file():
                continue
            if file_path.is_symlink():
                continue
            relative = file_path.relative_to(root_path)
            if _should_exclude(relative, exclude):
                continue
            if file_path.name in ENTRY_POINT_NAMES:
                # Prioritize top-level and src/ entry points
                entry_points.append(str(relative))
        except (PermissionError, OSError):
            continue

    # Sort: prefer shorter paths (closer to root)
    entry_points.sort(key=lambda p: p.count("/"))
    return entry_points


def _detect_services(root_path: Path, exclude: list[str]) -> list[ServiceInfo]:
    """Detect services or sub-projects in a monorepo/microservice architecture.

    Args:
        root_path: Root directory of the project.
        exclude: Directory names to skip.

    Returns:
        List of detected ServiceInfo instances.
    """
    services: list[ServiceInfo] = []

    # Check standard monorepo marker directories (packages/, apps/, services/, etc.)
    for marker_dir in MONOREPO_MARKERS:
        marker_path = root_path / marker_dir
        if not marker_path.is_dir():
            continue

        for sub_dir in sorted(marker_path.iterdir()):
            if not sub_dir.is_dir():
                continue
            if _should_exclude(sub_dir.relative_to(root_path), exclude):
                continue
            if _has_package_file(sub_dir):
                relative_path = str(sub_dir.relative_to(root_path))
                service = ServiceInfo(
                    name=sub_dir.name,
                    path=relative_path,
                )
                services.append(service)

    # Also check top-level directories that have their own package manifest
    # (generic monorepo pattern: backend/, frontend/, server/, client/, etc.)
    if not services:
        seen_names: set[str] = set()
        for item in sorted(root_path.iterdir()):
            if not item.is_dir():
                continue
            if item.name.startswith("."):
                continue
            if _should_exclude(item.relative_to(root_path), exclude):
                continue
            if _has_package_file(item) and item.name not in seen_names:
                seen_names.add(item.name)
                services.append(
                    ServiceInfo(
                        name=item.name,
                        path=item.name,
                    )
                )

    return services


def _has_indicator(root_path: Path, indicators: set[str], exclude: list[str]) -> bool:
    """Check if any of the indicator directory names exist in the project.

    Args:
        root_path: Root directory.
        indicators: Set of directory names to look for.
        exclude: Directory names to skip.

    Returns:
        True if any indicator directory is found.
    """
    for item in root_path.iterdir():
        if (
            item.is_dir()
            and item.name in indicators
            and not _should_exclude(item.relative_to(root_path), exclude)
        ):
            return True
    return False


def _has_file_indicator(root_path: Path, indicators: list[str], exclude: list[str]) -> bool:
    """Check if any indicator files or directories exist.

    First checks direct paths from root. If none found, falls back to
    recursive search for filename-only indicators (e.g. Dockerfile).

    Args:
        root_path: Root directory.
        indicators: File or directory names/paths to look for.
        exclude: Directory names to skip.

    Returns:
        True if any indicator is found.
    """
    for indicator in indicators:
        indicator_path = root_path / indicator
        if indicator_path.exists() and not _should_exclude(
            indicator_path.relative_to(root_path), exclude
        ):
            return True

    # Fallback: recursive search for simple filenames (no path separators)
    for indicator in indicators:
        if "/" in indicator or "\\" in indicator:
            continue  # Skip path-based indicators like .github/workflows
        for match in root_path.rglob(indicator):
            if match.is_symlink():
                continue
            try:
                rel = match.relative_to(root_path)
                if not _should_exclude(rel, exclude):
                    return True
            except (ValueError, OSError):
                continue

    return False


def _detect_modules(root_path: Path, exclude: list[str]) -> list[ModuleInfo]:
    """Detect logical modules by scanning top-level directories.

    Each significant top-level directory becomes a module. Files are
    classified by language using the extension map.

    Args:
        root_path: Root directory of the project.
        exclude: Directory names to skip.

    Returns:
        List of detected ModuleInfo instances.
    """
    modules: list[ModuleInfo] = []

    for item in sorted(root_path.iterdir()):
        if not item.is_dir():
            continue
        if _should_exclude(item.relative_to(root_path), exclude):
            continue
        # Skip hidden directories
        if item.name.startswith("."):
            continue

        files = _collect_files(item, root_path, exclude)
        if not files:
            continue

        # Determine primary language of the module
        lang_counts: dict[str, int] = {}
        for f in files:
            if f.language != "unknown":
                lang_counts[f.language] = lang_counts.get(f.language, 0) + 1

        primary_lang = max(lang_counts, key=lambda k: lang_counts[k]) if lang_counts else None

        module = ModuleInfo(
            name=item.name,
            path=str(item.relative_to(root_path)),
            files=files,
            language=primary_lang,
        )
        modules.append(module)

    return modules


def _collect_files(
    directory: Path,
    root_path: Path,
    exclude: list[str],
) -> list[FileInfo]:
    """Collect FileInfo for all source files in a directory tree.

    Args:
        directory: Directory to scan.
        root_path: Project root (for relative paths).
        exclude: Directory names to skip.

    Returns:
        List of FileInfo instances for source files.
    """
    files: list[FileInfo] = []

    for file_path in directory.rglob("*"):
        try:
            if not file_path.is_file():
                continue
            if file_path.is_symlink():
                continue
            relative = file_path.relative_to(root_path)
            if _should_exclude(relative, exclude):
                continue

            suffix = file_path.suffix.lower()
            language = EXTENSION_MAP.get(suffix, "unknown")
            if language in _NON_CODE_LANGUAGES:
                language = "unknown"

            files.append(
                FileInfo(
                    path=str(relative),
                    language=language,
                )
            )
        except (PermissionError, OSError):
            continue  # Skip unreadable files

    return files
