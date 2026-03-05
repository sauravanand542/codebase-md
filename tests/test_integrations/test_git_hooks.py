"""Tests for codebase_md.integrations.git_hooks."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from codebase_md.integrations.git_hooks import (
    HOOK_MARKER,
    GitHooksError,
    HookType,
    install_hook,
    is_hook_installed,
    list_installed_hooks,
    remove_all_hooks,
    remove_hook,
)


@pytest.fixture
def git_project(tmp_path: Path) -> Path:
    """Create a project with .git/ directory."""
    (tmp_path / ".git").mkdir()
    return tmp_path


class TestInstallHook:
    """Tests for install_hook function."""

    def test_installs_post_commit(self, git_project: Path) -> None:
        """Should install a post-commit hook."""
        hook_path = install_hook(git_project, HookType.POST_COMMIT)
        assert hook_path.is_file()
        assert hook_path.name == "post-commit"

    def test_hook_is_executable(self, git_project: Path) -> None:
        """Should make the hook executable."""
        hook_path = install_hook(git_project, HookType.POST_COMMIT)
        mode = hook_path.stat().st_mode
        assert mode & stat.S_IXUSR  # User execute bit

    def test_hook_contains_marker(self, git_project: Path) -> None:
        """Should contain the codebase-md marker comment."""
        hook_path = install_hook(git_project, HookType.POST_COMMIT)
        content = hook_path.read_text()
        assert HOOK_MARKER in content

    def test_hook_contains_scan_command(self, git_project: Path) -> None:
        """Should contain codebase scan + generate commands."""
        hook_path = install_hook(git_project, HookType.POST_COMMIT)
        content = hook_path.read_text()
        assert "codebase scan" in content
        assert "codebase generate" in content

    def test_backs_up_existing_hook(self, git_project: Path) -> None:
        """Should backup existing non-codebase hook before installing."""
        hooks_dir = git_project / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        existing = hooks_dir / "post-commit"
        existing.write_text("#!/bin/sh\necho 'custom hook'\n")

        install_hook(git_project, HookType.POST_COMMIT)
        backup = hooks_dir / "post-commit.backup"
        assert backup.is_file()
        assert "custom hook" in backup.read_text()

    def test_no_git_dir_raises(self, tmp_path: Path) -> None:
        """Should raise GitHooksError when no .git/ directory."""
        with pytest.raises(GitHooksError, match=r"No \.git/ directory"):
            install_hook(tmp_path, HookType.POST_COMMIT)

    def test_overwrites_own_hook(self, git_project: Path) -> None:
        """Should overwrite an existing codebase-md hook without backup."""
        install_hook(git_project, HookType.POST_COMMIT)
        # Install again — should not create backup
        install_hook(git_project, HookType.POST_COMMIT)
        hooks_dir = git_project / ".git" / "hooks"
        assert not (hooks_dir / "post-commit.backup").exists()

    def test_installs_pre_push(self, git_project: Path) -> None:
        """Should install a pre-push hook."""
        hook_path = install_hook(git_project, HookType.PRE_PUSH)
        assert hook_path.name == "pre-push"
        assert hook_path.is_file()


class TestRemoveHook:
    """Tests for remove_hook function."""

    def test_removes_installed_hook(self, git_project: Path) -> None:
        """Should remove a codebase-md hook."""
        install_hook(git_project, HookType.POST_COMMIT)
        result = remove_hook(git_project, HookType.POST_COMMIT)
        assert result is True
        hooks_dir = git_project / ".git" / "hooks"
        assert not (hooks_dir / "post-commit").is_file()

    def test_returns_false_when_not_installed(self, git_project: Path) -> None:
        """Should return False when no codebase-md hook exists."""
        result = remove_hook(git_project, HookType.POST_COMMIT)
        assert result is False

    def test_does_not_remove_foreign_hook(self, git_project: Path) -> None:
        """Should not remove hooks not created by codebase-md."""
        hooks_dir = git_project / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        foreign = hooks_dir / "post-commit"
        foreign.write_text("#!/bin/sh\necho 'foreign'\n")

        result = remove_hook(git_project, HookType.POST_COMMIT)
        assert result is False
        assert foreign.is_file()

    def test_restores_backup(self, git_project: Path) -> None:
        """Should restore backed-up hook after removal."""
        hooks_dir = git_project / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        existing = hooks_dir / "post-commit"
        existing.write_text("#!/bin/sh\necho 'original'\n")

        # Install (creates backup)
        install_hook(git_project, HookType.POST_COMMIT)
        # Remove (restores backup)
        remove_hook(git_project, HookType.POST_COMMIT)

        restored = hooks_dir / "post-commit"
        assert restored.is_file()
        assert "original" in restored.read_text()


class TestIsHookInstalled:
    """Tests for is_hook_installed function."""

    def test_true_when_installed(self, git_project: Path) -> None:
        """Should return True when our hook is installed."""
        install_hook(git_project, HookType.POST_COMMIT)
        assert is_hook_installed(git_project, HookType.POST_COMMIT) is True

    def test_false_when_not_installed(self, git_project: Path) -> None:
        """Should return False when no hook exists."""
        assert is_hook_installed(git_project, HookType.POST_COMMIT) is False

    def test_false_without_git_dir(self, tmp_path: Path) -> None:
        """Should return False when no .git/ directory."""
        assert is_hook_installed(tmp_path, HookType.POST_COMMIT) is False


class TestListInstalledHooks:
    """Tests for list_installed_hooks function."""

    def test_lists_installed_hooks(self, git_project: Path) -> None:
        """Should list all installed codebase-md hooks."""
        install_hook(git_project, HookType.POST_COMMIT)
        install_hook(git_project, HookType.PRE_PUSH)
        result = list_installed_hooks(git_project)
        assert HookType.POST_COMMIT in result
        assert HookType.PRE_PUSH in result

    def test_empty_when_none_installed(self, git_project: Path) -> None:
        """Should return empty list when nothing installed."""
        result = list_installed_hooks(git_project)
        assert result == []


class TestRemoveAllHooks:
    """Tests for remove_all_hooks function."""

    def test_removes_all(self, git_project: Path) -> None:
        """Should remove all installed hooks."""
        install_hook(git_project, HookType.POST_COMMIT)
        install_hook(git_project, HookType.PRE_PUSH)
        removed = remove_all_hooks(git_project)
        assert len(removed) == 2
        assert list_installed_hooks(git_project) == []
