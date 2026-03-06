"""Git hook management for codebase-md.

Installs, removes, and manages git hooks (post-commit, pre-push) that
automatically re-scan and regenerate context files after git operations.
"""

from __future__ import annotations

import os
import shlex
import stat
from enum import StrEnum
from pathlib import Path

# Marker comment to identify hooks managed by codebase-md
HOOK_MARKER = "# codebase-md auto-generated hook — do not edit"

HOOK_SCRIPT_TEMPLATE = """#!/bin/sh
{marker}
# Automatically re-scan and regenerate context files.
# Installed by: codebase hooks install
# Hook type: {hook_type}

# Run codebase-md scan + generate
codebase scan {root_path} && codebase generate {root_path}
"""


class GitHooksError(Exception):
    """Base exception for git hook operations."""


class HookType(StrEnum):
    """Supported git hook types."""

    POST_COMMIT = "post-commit"
    PRE_PUSH = "pre-push"


def _git_hooks_dir(root_path: Path) -> Path:
    """Return the path to the .git/hooks/ directory.

    Args:
        root_path: Project root directory.

    Returns:
        Path to .git/hooks/.

    Raises:
        GitHooksError: If .git/ directory does not exist.
    """
    git_dir = root_path / ".git"
    if not git_dir.is_dir():
        raise GitHooksError(
            f"No .git/ directory found in {root_path}. Initialize a git repository first: git init"
        )
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    return hooks_dir


def _hook_path(root_path: Path, hook_type: HookType) -> Path:
    """Return the full path to a specific hook file.

    Args:
        root_path: Project root directory.
        hook_type: Type of git hook.

    Returns:
        Path to the hook file.

    Raises:
        GitHooksError: If .git/ directory does not exist.
    """
    return _git_hooks_dir(root_path) / hook_type.value


def _is_our_hook(hook_file: Path) -> bool:
    """Check if a hook file was created by codebase-md.

    Args:
        hook_file: Path to the hook script.

    Returns:
        True if the hook contains our marker comment.
    """
    if not hook_file.is_file():
        return False
    try:
        content = hook_file.read_text(encoding="utf-8")
        return HOOK_MARKER in content
    except OSError:
        return False


def install_hook(root_path: Path, hook_type: HookType) -> Path:
    """Install a git hook for auto-regeneration.

    If a non-codebase-md hook already exists, it is backed up to
    <hook_name>.backup before being replaced.

    Args:
        root_path: Project root directory.
        hook_type: Type of git hook to install.

    Returns:
        Path to the installed hook file.

    Raises:
        GitHooksError: If the hook cannot be installed.
    """
    hook_file = _hook_path(root_path, hook_type)

    try:
        # Back up existing non-codebase-md hook
        if hook_file.is_file() and not _is_our_hook(hook_file):
            backup_path = hook_file.with_suffix(".backup")
            hook_file.rename(backup_path)

        # Write the hook script (shlex.quote prevents shell injection)
        script = HOOK_SCRIPT_TEMPLATE.format(
            marker=HOOK_MARKER,
            hook_type=hook_type.value,
            root_path=shlex.quote(str(root_path)),
        )
        hook_file.write_text(script, encoding="utf-8")

        # Make executable (unix only — on Windows this is a no-op)
        if os.name != "nt":
            current = hook_file.stat().st_mode
            hook_file.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        return hook_file
    except OSError as e:
        raise GitHooksError(f"Failed to install {hook_type.value} hook: {e}") from e


def remove_hook(root_path: Path, hook_type: HookType) -> bool:
    """Remove a codebase-md git hook.

    Only removes hooks that contain our marker comment. If a backup
    exists (from a previously overwritten hook), it is restored.

    Args:
        root_path: Project root directory.
        hook_type: Type of git hook to remove.

    Returns:
        True if a hook was removed, False if no codebase-md hook was found.

    Raises:
        GitHooksError: If the hook cannot be removed.
    """
    hook_file = _hook_path(root_path, hook_type)

    if not _is_our_hook(hook_file):
        return False

    try:
        hook_file.unlink()

        # Restore backup if it exists
        backup_path = hook_file.with_suffix(".backup")
        if backup_path.is_file():
            backup_path.rename(hook_file)

        return True
    except OSError as e:
        raise GitHooksError(f"Failed to remove {hook_type.value} hook: {e}") from e


def is_hook_installed(root_path: Path, hook_type: HookType) -> bool:
    """Check if a codebase-md hook is installed.

    Args:
        root_path: Project root directory.
        hook_type: Type of git hook to check.

    Returns:
        True if our hook is installed for this type.
    """
    try:
        hook_file = _hook_path(root_path, hook_type)
        return _is_our_hook(hook_file)
    except GitHooksError:
        return False


def install_all_hooks(root_path: Path) -> list[Path]:
    """Install all configured hooks based on .codebase/config.yaml.

    Reads the hooks configuration from the project's config and
    installs the corresponding git hooks.

    Args:
        root_path: Project root directory.

    Returns:
        List of paths to installed hook files.

    Raises:
        GitHooksError: If any hook cannot be installed.
    """
    from codebase_md.persistence.store import Store, StoreError

    installed: list[Path] = []

    # Read hook config
    try:
        store = Store(root_path)
        config = store.read_config()
    except StoreError:
        # If no config, install defaults (post-commit only)
        config = {"hooks": {"post_commit": True, "pre_push": False}}

    hooks_config = config.get("hooks", {})
    if not isinstance(hooks_config, dict):
        hooks_config = {"post_commit": True, "pre_push": False}

    if hooks_config.get("post_commit", True):
        path = install_hook(root_path, HookType.POST_COMMIT)
        installed.append(path)

    if hooks_config.get("pre_push", False):
        path = install_hook(root_path, HookType.PRE_PUSH)
        installed.append(path)

    return installed


def remove_all_hooks(root_path: Path) -> list[HookType]:
    """Remove all codebase-md hooks from the project.

    Args:
        root_path: Project root directory.

    Returns:
        List of hook types that were removed.

    Raises:
        GitHooksError: If any hook cannot be removed.
    """
    removed: list[HookType] = []
    for hook_type in HookType:
        if remove_hook(root_path, hook_type):
            removed.append(hook_type)
    return removed


def list_installed_hooks(root_path: Path) -> list[HookType]:
    """List all codebase-md hooks that are currently installed.

    Args:
        root_path: Project root directory.

    Returns:
        List of installed hook types.
    """
    installed: list[HookType] = []
    for hook_type in HookType:
        if is_hook_installed(root_path, hook_type):
            installed.append(hook_type)
    return installed
