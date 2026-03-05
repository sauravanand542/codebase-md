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
from codebase_md.model.project import ProjectModel, ScanMetadata
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
) -> ScanResult:
    """Run the full scanning pipeline on a project.

    Orchestrates all sub-scanners in sequence:
    1. Language detection
    2. Structure analysis (architecture + modules)
    3. Dependency parsing
    4. Convention inference (tree-sitter + regex)
    5. AST analysis (exports, imports, purpose)
    6. Git history analysis (hotspots, contributors)

    Assembles results into a ProjectModel and optionally persists
    it to .codebase/project.json.

    Args:
        root_path: Root directory of the project to scan.
        exclude: Directory/file names to skip. Uses defaults if None.
        persist: Whether to save results to .codebase/project.json.

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
    dependencies = _run_dependency_parsing(root_path, warnings)

    # Step 4: Framework enrichment (enrich language list with framework data)
    _run_framework_detection(root_path, warnings)

    # Step 5: Convention inference
    conventions = _run_convention_inference(root_path, exclude_list, warnings)

    # Step 6: AST analysis (enrich modules with file-level data)
    file_infos = _run_ast_analysis(root_path, exclude_list, warnings)
    modules = _enrich_modules_with_ast(modules, file_infos)

    # Step 7: Git analysis
    git_info = _run_git_analysis(root_path, warnings)
    git_sha = git_info.branch if git_info else _get_git_sha(root_path)
    # Use actual git SHA, not branch name
    git_sha = _get_git_sha(root_path)

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
        root_path=str(root_path),
        languages=languages,
        architecture=architecture,
        modules=modules,
        dependencies=dependencies,
        conventions=conventions,
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
) -> list[DependencyInfo]:
    """Run dependency parsing, capturing warnings on failure.

    Args:
        root_path: Project root.
        warnings: List to append warnings to.

    Returns:
        List of DependencyInfo instances.
    """
    try:
        return parse_dependencies(root_path)
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
) -> list[dict[str, str]]:
    """Run framework detection, capturing warnings on failure.

    Args:
        root_path: Project root.
        warnings: List to append warnings to.

    Returns:
        List of detected framework dicts.
    """
    try:
        return detect_frameworks(root_path)
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
