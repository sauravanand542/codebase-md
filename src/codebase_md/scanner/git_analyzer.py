"""Git history analysis for codebase scanning.

Analyzes git history to determine change frequency (hotspots),
contributors per module, and recent activity areas. All data
is gathered via subprocess calls to git.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class GitAnalysisError(Exception):
    """Raised when git analysis fails."""


@dataclass
class FileActivity:
    """Activity data for a single file.

    Attributes:
        path: Relative path from project root.
        commit_count: Number of commits touching this file.
        last_modified: ISO date of last modification.
        contributors: Set of author names who modified this file.
    """

    path: str
    commit_count: int = 0
    last_modified: str = ""
    contributors: set[str] = field(default_factory=set)


@dataclass
class GitInfo:
    """Aggregated git analysis results.

    Attributes:
        total_commits: Total number of commits in the repo.
        contributors: All contributors (author names).
        hotspots: Most frequently changed files (top N by commit count).
        recent_files: Recently modified files (last 30 days).
        branch: Current branch name.
        file_activities: Per-file activity data.
    """

    total_commits: int = 0
    contributors: list[str] = field(default_factory=list)
    hotspots: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    branch: str = ""
    file_activities: dict[str, FileActivity] = field(default_factory=dict)


def _run_git(
    args: list[str],
    cwd: Path,
    timeout: int = 15,
) -> str | None:
    """Run a git command and return stdout, or None on failure.

    Args:
        args: Git command arguments (without 'git' prefix).
        cwd: Working directory for the command.
        timeout: Command timeout in seconds.

    Returns:
        stdout as string, or None if the command failed.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _is_git_repo(root_path: Path) -> bool:
    """Check if the path is inside a git repository.

    Args:
        root_path: Directory to check.

    Returns:
        True if inside a git repo.
    """
    return _run_git(["rev-parse", "--is-inside-work-tree"], root_path) == "true"


def _get_branch(root_path: Path) -> str:
    """Get the current branch name.

    Args:
        root_path: Project root.

    Returns:
        Branch name, or empty string if unavailable.
    """
    result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], root_path)
    return result or ""


def _get_total_commits(root_path: Path) -> int:
    """Get the total number of commits in the repo.

    Args:
        root_path: Project root.

    Returns:
        Total commit count.
    """
    result = _run_git(["rev-list", "--count", "HEAD"], root_path)
    if result:
        try:
            return int(result)
        except ValueError:
            pass
    return 0


def _get_contributors(root_path: Path) -> list[str]:
    """Get all unique contributors (author names), sorted by commit count.

    Args:
        root_path: Project root.

    Returns:
        List of author names, most prolific first.
    """
    result = _run_git(["shortlog", "-sn", "--no-merges", "HEAD"], root_path)
    if not result:
        return []

    contributors: list[str] = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "  123  Author Name"
        parts = line.split("\t", 1)
        if len(parts) == 2:
            contributors.append(parts[1].strip())
        else:
            # Fallback: split on whitespace after the count
            stripped = line.lstrip()
            space_idx = stripped.find(" ")
            if space_idx > 0:
                contributors.append(stripped[space_idx:].strip())

    return contributors


def _get_file_change_counts(root_path: Path, max_files: int = 50) -> list[tuple[str, int]]:
    """Get files sorted by number of commits (most changed first).

    Args:
        root_path: Project root.
        max_files: Maximum number of files to return.

    Returns:
        List of (file_path, commit_count) tuples.
    """
    result = _run_git(
        ["log", "-n", "500", "--pretty=format:", "--name-only", "--no-merges", "HEAD"],
        root_path,
        timeout=30,
    )
    if not result:
        return []

    file_counts: dict[str, int] = {}
    for line in result.splitlines():
        line = line.strip()
        if line:
            file_counts[line] = file_counts.get(line, 0) + 1

    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_files[:max_files]


def _get_recent_files(root_path: Path, days: int = 30) -> list[str]:
    """Get files modified in the last N days.

    Args:
        root_path: Project root.
        days: Number of days to look back.

    Returns:
        List of recently modified file paths (deduplicated).
    """
    result = _run_git(
        [
            "log",
            "-n",
            "200",
            f"--since={days} days ago",
            "--pretty=format:",
            "--name-only",
            "--no-merges",
            "HEAD",
        ],
        root_path,
    )
    if not result:
        return []

    seen: set[str] = set()
    recent: list[str] = []
    for line in result.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            recent.append(line)

    return recent


def _get_file_contributors(root_path: Path, file_path: str) -> list[str]:
    """Get contributors for a specific file.

    Args:
        root_path: Project root.
        file_path: Relative path to the file.

    Returns:
        List of contributor names for the file.
    """
    result = _run_git(
        ["log", "--pretty=format:%aN", "--no-merges", "--", file_path],
        root_path,
    )
    if not result:
        return []

    seen: set[str] = set()
    contributors: list[str] = []
    for line in result.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            contributors.append(line)

    return contributors


# --- Main Entry Point ---


def analyze_git(root_path: Path) -> GitInfo | None:
    """Analyze git history for the project.

    Gathers commit counts, contributors, file change frequency
    (hotspots), and recent activity from the git log.

    Args:
        root_path: Root directory of the project.

    Returns:
        GitInfo with analysis results, or None if not a git repo.

    Raises:
        GitAnalysisError: If root_path is invalid.
    """
    if not root_path.exists():
        raise GitAnalysisError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise GitAnalysisError(f"Path is not a directory: {root_path}")

    if not _is_git_repo(root_path):
        return None

    branch = _get_branch(root_path)
    total_commits = _get_total_commits(root_path)
    contributors = _get_contributors(root_path)
    file_changes = _get_file_change_counts(root_path)
    recent = _get_recent_files(root_path)

    hotspots = [f for f, _ in file_changes[:20]]

    # Build per-file activity data for hotspots
    file_activities: dict[str, FileActivity] = {}
    for file_path, count in file_changes:
        file_activities[file_path] = FileActivity(
            path=file_path,
            commit_count=count,
        )

    # Enrich top hotspot files with contributor data
    for file_path, _ in file_changes[:10]:
        contributors_for_file = _get_file_contributors(root_path, file_path)
        if file_path in file_activities and contributors_for_file:
            file_activities[file_path].contributors = set(contributors_for_file)

    return GitInfo(
        total_commits=total_commits,
        contributors=contributors,
        hotspots=hotspots,
        recent_files=recent,
        branch=branch,
        file_activities=file_activities,
    )
