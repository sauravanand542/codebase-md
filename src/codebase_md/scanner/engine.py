"""Scanner engine — orchestrates all scanners to build a ProjectModel.

This is the main entry point for the scanning pipeline. It coordinates
language detection, structure analysis, dependency parsing, convention
inference, AST analysis, and git history analysis, then assembles the
results into a complete ProjectModel and persists it.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

from codebase_md import __version__
from codebase_md.model.architecture import ArchitectureInfo
from codebase_md.model.convention import ConventionSet
from codebase_md.model.dependency import DependencyInfo
from codebase_md.model.module import FileInfo, ModuleInfo
from codebase_md.model.project import GitInsights, ProjectModel, ScanMetadata
from codebase_md.persistence.store import Store
from codebase_md.scanner.ast_analyzer import ASTAnalysisError, analyze_files
from codebase_md.scanner.convention_inferrer import ConventionInferenceError, infer_conventions
from codebase_md.scanner.dependency_parser import DependencyParseError, parse_dependencies
from codebase_md.scanner.git_analyzer import GitAnalysisError, GitInfo, analyze_git
from codebase_md.scanner.language_detector import (
    DEFAULT_EXCLUDES,
    LanguageDetectionError,
    detect_frameworks,
    detect_languages,
)
from codebase_md.scanner.structure_analyzer import (
    StructureAnalysisError,
    analyze_structure,
)


class ScannerError(Exception):
    """Base exception for scanner engine operations."""


class ScanResult:
    """Container for scan results with status information.

    Attributes:
        model: The assembled ProjectModel.
        warnings: Non-fatal issues encountered during scanning.
        duration: How long the scan took in seconds.
    """

    def __init__(
        self,
        model: ProjectModel,
        warnings: list[str],
        duration: float,
    ) -> None:
        self.model = model
        self.warnings = warnings
        self.duration = duration


def scan_project(
    root_path: Path,
    exclude: list[str] | None = None,
    persist: bool = True,
    depth: str = "full",
) -> ScanResult:
    """Run the full scanning pipeline on a project.

    Orchestrates all sub-scanners in sequence:
    1. Language detection
    2. Structure analysis (architecture + modules)
    3. Dependency parsing
    4. Convention inference (tree-sitter + regex)
    5. AST analysis (exports, imports, purpose) — skipped in shallow mode
    6. Git history analysis (hotspots, contributors)

    Assembles results into a ProjectModel and optionally persists
    it to .codebase/project.json.

    Args:
        root_path: Root directory of the project to scan.
        exclude: Directory/file names to skip. Uses defaults if None.
        persist: Whether to save results to .codebase/project.json.
        depth: Scan depth — 'full' (default) or 'shallow' (skip AST).

    Returns:
        ScanResult containing the ProjectModel, warnings, and duration.

    Raises:
        ScannerError: If the root path is invalid or a critical scanner fails.
    """
    if not root_path.exists():
        raise ScannerError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise ScannerError(f"Path is not a directory: {root_path}")

    root_path = root_path.resolve()
    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES
    warnings: list[str] = []
    start_time = time.monotonic()

    # Step 1: Language Detection
    languages = _run_language_detection(root_path, exclude_list, warnings)

    # Step 2: Structure Analysis
    architecture, modules = _run_structure_analysis(root_path, exclude_list, warnings)

    # Step 3: Dependency Parsing
    # Always scan module directories for manifests (not just monorepo sub-packages).
    # Many projects keep manifests in subdirectories (e.g. backend/requirements.txt,
    # frontend/package.json) rather than at the project root.
    from codebase_md.model.architecture import ArchitectureType as _ArchType

    extra_scan_dirs: list[Path] = []
    # Add module directories
    for mod in modules:
        mod_dir = root_path / mod.path
        if mod_dir.is_dir() and mod_dir != root_path:
            extra_scan_dirs.append(mod_dir)
    # Add monorepo service directories (may differ from modules)
    if architecture.architecture_type == _ArchType.MONOREPO and architecture.services:
        for svc in architecture.services:
            svc_dir = root_path / svc.path
            if svc_dir.is_dir() and svc_dir not in extra_scan_dirs:
                extra_scan_dirs.append(svc_dir)

    scan_extra = extra_scan_dirs if extra_scan_dirs else None
    dependencies = _run_dependency_parsing(root_path, warnings, extra_dirs=scan_extra)

    # Step 4: Framework enrichment (enrich language list with framework data)
    frameworks_data = _run_framework_detection(root_path, warnings, extra_dirs=scan_extra)
    frameworks = sorted({d["framework"] for d in frameworks_data if "framework" in d})

    # Step 5: Convention inference
    conventions = _run_convention_inference(root_path, exclude_list, warnings)

    # Step 6: AST analysis (enrich modules with file-level data) — skip in shallow mode
    if depth == "shallow":
        file_infos: list[FileInfo] = []
        warnings.append("AST analysis skipped (shallow scan mode)")
    else:
        file_infos = _run_ast_analysis(root_path, exclude_list, warnings)
    modules = _enrich_modules_with_ast(modules, file_infos)

    # Step 7: Git analysis
    git_info = _run_git_analysis(root_path, warnings)
    git_sha = _get_git_sha(root_path)

    # Step 8: Extract project description
    description = _extract_project_description(root_path, warnings)

    # Step 9: Extract real build/test/lint commands
    build_commands = _extract_build_commands(root_path, languages, warnings, extra_dirs=scan_extra)

    # Step 10: Build git insights
    git_insights = _build_git_insights(git_info)

    # Assemble the ProjectModel
    duration = time.monotonic() - start_time
    metadata = ScanMetadata(
        scanned_at=datetime.now(tz=UTC),
        version=__version__,
        git_sha=git_sha,
        scan_duration=round(duration, 3),
    )

    project_name = root_path.name
    model = ProjectModel(
        name=project_name,
        description=description,
        root_path=str(root_path),
        languages=languages,
        frameworks=frameworks,
        build_commands=build_commands,
        architecture=architecture,
        modules=modules,
        dependencies=dependencies,
        conventions=conventions,
        git_insights=git_insights,
        metadata=metadata,
    )

    # Persist if requested
    if persist:
        _persist_result(root_path, model, warnings)

    return ScanResult(
        model=model,
        warnings=warnings,
        duration=round(duration, 3),
    )


def _run_language_detection(
    root_path: Path,
    exclude: list[str],
    warnings: list[str],
) -> list[str]:
    """Run language detection, capturing warnings on failure.

    Args:
        root_path: Project root.
        exclude: Exclusion list.
        warnings: List to append warnings to.

    Returns:
        List of detected language names.
    """
    try:
        return detect_languages(root_path, exclude)
    except LanguageDetectionError as e:
        warnings.append(f"Language detection failed: {e}")
        return []


def _run_structure_analysis(
    root_path: Path,
    exclude: list[str],
    warnings: list[str],
) -> tuple[ArchitectureInfo, list[ModuleInfo]]:
    """Run structure analysis, capturing warnings on failure.

    Args:
        root_path: Project root.
        exclude: Exclusion list.
        warnings: List to append warnings to.

    Returns:
        Tuple of (ArchitectureInfo, list[ModuleInfo]).
    """
    from codebase_md.model.architecture import (
        ArchitectureInfo as _ArchitectureInfo,
    )

    try:
        return analyze_structure(root_path, exclude)
    except StructureAnalysisError as e:
        warnings.append(f"Structure analysis failed: {e}")
        return _ArchitectureInfo(), []


def _run_dependency_parsing(
    root_path: Path,
    warnings: list[str],
    extra_dirs: list[Path] | None = None,
) -> list[DependencyInfo]:
    """Run dependency parsing, capturing warnings on failure.

    Args:
        root_path: Project root.
        warnings: List to append warnings to.
        extra_dirs: Additional directories for monorepo sub-packages.

    Returns:
        List of DependencyInfo instances.
    """
    try:
        return parse_dependencies(root_path, extra_dirs=extra_dirs)
    except DependencyParseError as e:
        warnings.append(f"Dependency parsing failed: {e}")
        return []


def _run_convention_inference(
    root_path: Path,
    exclude: list[str],
    warnings: list[str],
) -> ConventionSet:
    """Run convention inference, capturing warnings on failure.

    Args:
        root_path: Project root.
        exclude: Exclusion list.
        warnings: List to append warnings to.

    Returns:
        Detected ConventionSet.
    """
    try:
        return infer_conventions(root_path, exclude)
    except ConventionInferenceError as e:
        warnings.append(f"Convention inference failed: {e}")
        return ConventionSet()


def _run_ast_analysis(
    root_path: Path,
    exclude: list[str],
    warnings: list[str],
) -> list[FileInfo]:
    """Run AST analysis on source files, capturing warnings on failure.

    Args:
        root_path: Project root.
        exclude: Exclusion list.
        warnings: List to append warnings to.

    Returns:
        List of FileInfo with exports, imports, purpose.
    """
    try:
        return analyze_files(root_path, exclude)
    except ASTAnalysisError as e:
        warnings.append(f"AST analysis failed: {e}")
        return []


def _enrich_modules_with_ast(
    modules: list[ModuleInfo],
    file_infos: list[FileInfo],
) -> list[ModuleInfo]:
    """Enrich module data with AST-analyzed file information.

    Matches FileInfo entries to their parent modules by path prefix
    and replaces the module's files list with enriched data.

    Args:
        modules: Existing modules from structure analysis.
        file_infos: File-level analysis from AST analyzer.

    Returns:
        Updated list of ModuleInfo with enriched file data.
    """
    if not file_infos:
        return modules

    # Build a lookup: module_path → list of FileInfo
    module_files: dict[str, list[FileInfo]] = {}
    for fi in file_infos:
        for mod in modules:
            if fi.path.startswith(mod.path):
                module_files.setdefault(mod.path, []).append(fi)
                break

    # Rebuild modules with enriched file lists
    enriched: list[ModuleInfo] = []
    for mod in modules:
        new_files = module_files.get(mod.path, [])
        if new_files:
            # Merge: keep existing files that weren't re-analyzed, add new ones
            existing_paths = {f.path for f in new_files}
            kept = [f for f in mod.files if f.path not in existing_paths]
            enriched.append(
                ModuleInfo(
                    name=mod.name,
                    path=mod.path,
                    purpose=mod.purpose,
                    files=kept + new_files,
                    language=mod.language,
                    framework=mod.framework,
                )
            )
        else:
            enriched.append(mod)

    return enriched


def _run_git_analysis(
    root_path: Path,
    warnings: list[str],
) -> GitInfo | None:
    """Run git history analysis, capturing warnings on failure.

    Args:
        root_path: Project root.
        warnings: List to append warnings to.

    Returns:
        GitInfo instance, or None if not a git repo.
    """
    try:
        return analyze_git(root_path)
    except GitAnalysisError as e:
        warnings.append(f"Git analysis failed: {e}")
        return None


def _run_framework_detection(
    root_path: Path,
    warnings: list[str],
    extra_dirs: list[Path] | None = None,
) -> list[dict[str, str]]:
    """Run framework detection, capturing warnings on failure.

    Args:
        root_path: Project root.
        warnings: List to append warnings to.
        extra_dirs: Additional directories for monorepo sub-packages.

    Returns:
        List of detected framework dicts.
    """
    try:
        return detect_frameworks(root_path, extra_dirs=extra_dirs)
    except LanguageDetectionError as e:
        warnings.append(f"Framework detection failed: {e}")
        return []


def _get_git_sha(root_path: Path) -> str | None:
    """Get the current git SHA for the project.

    Args:
        root_path: Project root.

    Returns:
        The git HEAD SHA string, or None if not a git repo.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _persist_result(
    root_path: Path,
    model: ProjectModel,
    warnings: list[str],
) -> None:
    """Persist the scan result to .codebase/project.json.

    Initializes .codebase/ if it doesn't exist yet.

    Args:
        root_path: Project root.
        model: The ProjectModel to persist.
        warnings: List to append warnings to.
    """
    try:
        store = Store(root_path)
        if not store.is_initialized:
            store.init()
        store.write_project(model)
    except Exception as e:
        warnings.append(f"Failed to persist scan results: {e}")


def _extract_project_description(
    root_path: Path,
    warnings: list[str],
) -> str:
    """Extract a project description from README, pyproject.toml, or package.json.

    Tries sources in priority order:
    1. README.md — first non-empty, non-heading paragraph
    2. pyproject.toml — [project].description
    3. package.json — "description" field

    Args:
        root_path: Project root.
        warnings: List to append warnings to.

    Returns:
        Project description string, or "" if not found.
    """
    # Try README.md first
    for readme_name in (
        "README.md",
        "readme.md",
        "README.markdown",
        "README.rst",
        "README",
    ):
        readme_path = root_path / readme_name
        if readme_path.is_file():
            try:
                content = readme_path.read_text(encoding="utf-8", errors="replace")
                desc = _extract_readme_description(content)
                if desc:
                    return desc
            except OSError:
                pass

    # Try pyproject.toml
    pyproject_path = root_path / "pyproject.toml"
    if pyproject_path.is_file():
        try:
            content = pyproject_path.read_text(encoding="utf-8")
            desc = _extract_pyproject_description(content)
            if desc:
                return desc
        except OSError:
            pass

    # Try package.json
    package_json = root_path / "package.json"
    if package_json.is_file():
        try:
            import json

            data = json.loads(package_json.read_text(encoding="utf-8"))
            desc = data.get("description", "")
            if desc and isinstance(desc, str):
                return str(desc.strip())
        except (OSError, json.JSONDecodeError):
            pass

    return ""


def _extract_readme_description(content: str) -> str:
    """Extract the first meaningful paragraph from README content.

    Skips headings, badges, blank lines. Returns the first paragraph
    that looks like prose (not a code block or image).

    Args:
        content: README file content.

    Returns:
        First paragraph text, or "".
    """
    lines = content.splitlines()
    paragraph_lines: list[str] = []
    found_heading = False

    for line in lines:
        stripped = line.strip()

        # Skip blank lines before content
        if not stripped:
            if paragraph_lines:
                break  # End of first paragraph
            continue

        # Skip headings
        if stripped.startswith("#"):
            if found_heading and paragraph_lines:
                break  # Second heading → done
            found_heading = True
            continue

        # Skip badges (markdown images/links starting lines)
        if stripped.startswith("[![") or stripped.startswith("!["):
            continue

        # Skip link reference definitions like [name]: url
        if stripped.startswith("[") and "]:" in stripped:
            continue

        # Skip code blocks
        if stripped.startswith("```"):
            if paragraph_lines:
                break
            continue

        # Skip HTML tags
        if stripped.startswith("<"):
            continue

        # This is content
        paragraph_lines.append(stripped)

    if not paragraph_lines:
        return ""

    result = " ".join(paragraph_lines)
    # Truncate if very long
    if len(result) > 500:
        result = result[:497] + "..."
    return result


def _extract_pyproject_description(content: str) -> str:
    """Extract description from pyproject.toml content.

    Uses tomllib for reliable parsing, with regex fallback.

    Args:
        content: pyproject.toml file content.

    Returns:
        Description string, or "".
    """
    # Try tomllib first
    try:
        import tomllib

        data = tomllib.loads(content)
        desc = data.get("project", {}).get("description", "")
        if desc and isinstance(desc, str):
            return str(desc.strip())
    except Exception:
        pass

    # Regex fallback
    import re

    match = re.search(r'^description\s*=\s*"([^"]*)"', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def _extract_build_commands(
    root_path: Path,
    languages: list[str],
    warnings: list[str],
    extra_dirs: list[Path] | None = None,
) -> list[str]:
    """Extract actual build/test/lint commands from project configuration.

    Reads scripts from pyproject.toml, package.json, and Makefile to find
    real commands rather than guessing from language. Also scans module
    directories (extra_dirs) for manifests.

    Args:
        root_path: Project root.
        languages: Detected languages.
        warnings: List to append warnings to.
        extra_dirs: Additional directories to scan for manifests
            (e.g. module paths like backend/, frontend/).

    Returns:
        List of command strings (e.g. "pytest", "npm test").
    """
    commands: list[str] = []
    seen_commands: set[str] = set()

    # Collect all directories to scan: root + extra_dirs
    dirs_to_scan = [root_path]
    if extra_dirs:
        dirs_to_scan.extend(extra_dirs)

    for scan_dir in dirs_to_scan:
        if not scan_dir.is_dir():
            continue

        # Compute prefix for subdirectory commands (e.g. "cd backend && ")
        if scan_dir == root_path:
            prefix = ""
        else:
            rel = scan_dir.relative_to(root_path)
            prefix = f"cd {rel} && "

        # Try pyproject.toml [project.scripts]
        pyproject_path = scan_dir / "pyproject.toml"
        if pyproject_path.is_file():
            try:
                content = pyproject_path.read_text(encoding="utf-8")
                for cmd in _extract_pyproject_commands(content, scan_dir):
                    full_cmd = f"{prefix}{cmd}" if prefix else cmd
                    if full_cmd not in seen_commands:
                        seen_commands.add(full_cmd)
                        commands.append(full_cmd)
            except OSError:
                pass

        # Try requirements.txt → pip install
        requirements_path = scan_dir / "requirements.txt"
        if requirements_path.is_file():
            full_cmd = (
                f"{prefix}pip install -r requirements.txt"
                if prefix
                else "pip install -r requirements.txt"
            )
            if full_cmd not in seen_commands:
                seen_commands.add(full_cmd)
                commands.append(full_cmd)

        # Try package.json scripts
        package_json = scan_dir / "package.json"
        if package_json.is_file():
            try:
                import json

                data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                if isinstance(scripts, dict):
                    for key in ("dev", "build", "test", "lint", "start", "format", "typecheck"):
                        if key in scripts:
                            full_cmd = f"{prefix}npm run {key}" if prefix else f"npm run {key}"
                            if full_cmd not in seen_commands:
                                seen_commands.add(full_cmd)
                                commands.append(full_cmd)
            except (OSError, json.JSONDecodeError):
                pass

        # Try Makefile targets
        makefile_path = scan_dir / "Makefile"
        if makefile_path.is_file():
            try:
                content = makefile_path.read_text(encoding="utf-8")
                import re

                targets = re.findall(r"^([a-zA-Z_][a-zA-Z0-9_-]*):", content, re.MULTILINE)
                useful_targets = [
                    t
                    for t in targets
                    if t
                    in (
                        "build",
                        "test",
                        "lint",
                        "format",
                        "install",
                        "dev",
                        "run",
                        "clean",
                        "check",
                        "deploy",
                        "start",
                    )
                ]
                for t in useful_targets:
                    full_cmd = f"{prefix}make {t}" if prefix else f"make {t}"
                    if full_cmd not in seen_commands:
                        seen_commands.add(full_cmd)
                        commands.append(full_cmd)
            except OSError:
                pass

    return commands


def _extract_pyproject_commands(content: str, root_path: Path) -> list[str]:
    """Extract build commands from pyproject.toml.

    Uses tomllib for reliable parsing, with regex fallback.
    Looks for [project.scripts], tool.ruff, tool.pytest, tool.mypy sections
    to infer real commands.

    Args:
        content: pyproject.toml file content.
        root_path: Project root for checking tool availability.

    Returns:
        List of command strings.
    """
    commands: list[str] = []

    # Try tomllib first
    try:
        import tomllib

        data = tomllib.loads(content)
        scripts = data.get("project", {}).get("scripts", {})
        if scripts:
            cmd_name = next(iter(scripts))
            commands.append(f"pip install -e '.[dev]'  # provides '{cmd_name}' command")

        tool = data.get("tool", {})
        if "pytest" in tool or "pytest" in str(data.get("project", {}).get("dependencies", [])):
            commands.append("pytest")
        if "ruff" in tool:
            commands.append("ruff check .")
            commands.append("ruff format .")
        if "mypy" in tool:
            commands.append("mypy src/")

        return commands
    except Exception:
        pass

    # Regex fallback
    import re

    script_match = re.search(
        r"^\[project\.scripts\]\s*\n((?:[^\[].+\n)*)",
        content,
        re.MULTILINE,
    )
    if script_match:
        for line in script_match.group(1).splitlines():
            line = line.strip()
            if "=" in line:
                cmd_name = line.split("=")[0].strip().strip('"')
                if cmd_name:
                    commands.append(f"pip install -e '.[dev]'  # provides '{cmd_name}' command")
                    break

    if "[tool.pytest" in content or "pytest" in content.lower():
        commands.append("pytest")
    if "[tool.ruff" in content:
        commands.append("ruff check .")
        commands.append("ruff format .")
    if "[tool.mypy" in content:
        commands.append("mypy src/")

    return commands


def _build_git_insights(git_info: GitInfo | None) -> GitInsights:
    """Build GitInsights model from raw git analysis data.

    Args:
        git_info: Raw git analysis results, or None.

    Returns:
        Populated GitInsights model.
    """
    if not git_info:
        return GitInsights()

    return GitInsights(
        total_commits=git_info.total_commits,
        contributors=git_info.contributors,
        hotspots=git_info.hotspots[:10],
        recent_files=git_info.recent_files[:10],
        branch=git_info.branch,
    )
