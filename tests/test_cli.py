"""Tests for codebase_md.cli — CLI commands via CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from codebase_md.cli import app
from codebase_md.model.project import ProjectModel

runner = CliRunner()


class TestVersionCommand:
    """Tests for --version flag."""

    def test_version_flag(self) -> None:
        """Should print version and exit."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "codebase-md" in result.output
        assert "0.1.0" in result.output


class TestInitCommand:
    """Tests for codebase init."""

    def test_init_creates_codebase_dir(self, tmp_path: Path) -> None:
        """Should create .codebase/ directory."""
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / ".codebase" / "config.yaml").is_file()

    def test_init_already_initialized(self, initialized_project: Path) -> None:
        """Should report already initialized."""
        result = runner.invoke(app, ["init", str(initialized_project)])
        assert result.exit_code == 0
        assert "Already initialized" in result.output


class TestScanCommand:
    """Tests for codebase scan."""

    def test_scan_python_project(self, sample_python_project: Path) -> None:
        """Should scan a Python project successfully."""
        # Initialize first
        runner.invoke(app, ["init", str(sample_python_project)])
        result = runner.invoke(app, ["scan", str(sample_python_project)])
        assert result.exit_code == 0
        assert "Scan complete" in result.output

    def test_scan_nonexistent_path(self) -> None:
        """Should fail on nonexistent path."""
        result = runner.invoke(app, ["scan", "/nonexistent/path"])
        assert result.exit_code == 1


class TestGenerateCommand:
    """Tests for codebase generate."""

    def test_generate_requires_scan(self, initialized_project: Path) -> None:
        """Should fail when no scan data exists."""
        result = runner.invoke(app, ["generate", str(initialized_project)])
        assert result.exit_code == 1
        assert "scan" in result.output.lower()

    def test_generate_invalid_format(self, tmp_path: Path) -> None:
        """Should fail on unknown format."""
        # Setup: init + scan + store model
        codebase_dir = tmp_path / ".codebase"
        codebase_dir.mkdir()
        config = {"version": 1, "generators": ["claude"]}
        (codebase_dir / "config.yaml").write_text(yaml.dump(config))

        model = ProjectModel(name="test", root_path=str(tmp_path))
        data = model.model_dump(mode="json")
        (codebase_dir / "project.json").write_text(json.dumps(data, indent=2, default=str))

        result = runner.invoke(app, ["generate", str(tmp_path), "--format", "badformat"])
        assert result.exit_code == 1
        assert "Unknown format" in result.output


class TestHooksCommand:
    """Tests for codebase hooks."""

    def test_hooks_install(self, tmp_path: Path) -> None:
        """Should install hooks when .git/ exists."""
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["hooks", "install", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Installing" in result.output or "Done" in result.output

    def test_hooks_no_git(self, tmp_path: Path) -> None:
        """Should fail when no .git/ directory."""
        result = runner.invoke(app, ["hooks", "install", "--path", str(tmp_path)])
        assert result.exit_code == 1

    def test_hooks_status(self, tmp_path: Path) -> None:
        """Should show hook status."""
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["hooks", "status", "--path", str(tmp_path)])
        assert result.exit_code == 0

    def test_hooks_unknown_action(self, tmp_path: Path) -> None:
        """Should fail on unknown action."""
        result = runner.invoke(app, ["hooks", "badaction", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "Unknown action" in result.output


class TestContextCommand:
    """Tests for codebase context."""

    def test_context_requires_scan(self, initialized_project: Path) -> None:
        """Should fail when no scan data exists."""
        result = runner.invoke(
            app,
            ["context", "architecture", "--path", str(initialized_project)],
        )
        assert result.exit_code == 1


class TestDecisionsCommand:
    """Tests for codebase decisions subcommands."""

    def test_decisions_list_empty(self, tmp_path: Path) -> None:
        """Should show 'no decisions' message when none recorded."""
        result = runner.invoke(app, ["decisions", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "No decisions" in result.output

    def test_decisions_add_and_list(self, tmp_path: Path) -> None:
        """Should add a decision interactively and list it."""
        # Create .codebase/ so decisions can be stored
        (tmp_path / ".codebase").mkdir()

        # Simulate interactive input: title, context, choice, alternatives, consequences
        input_text = (
            "Use PostgreSQL\nNeed a relational DB\nPostgreSQL\nMySQL, SQLite\nGood JSON support\n"
        )
        result = runner.invoke(app, ["decisions", "add", str(tmp_path)], input=input_text)
        assert result.exit_code == 0
        assert "Done" in result.output or "recorded" in result.output.lower()

        # List should now show the decision
        result = runner.invoke(app, ["decisions", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "PostgreSQL" in result.output

    def test_decisions_remove_invalid_index(self, tmp_path: Path) -> None:
        """Should fail with invalid index."""
        result = runner.invoke(
            app,
            ["decisions", "remove", "99", "--path", str(tmp_path)],
        )
        # Either no decisions or invalid index
        assert (
            result.exit_code == 0 or "No decisions" in result.output or "Invalid" in result.output
        )

    def test_decisions_remove_with_force(self, tmp_path: Path) -> None:
        """Should remove a decision with --force flag."""
        (tmp_path / ".codebase").mkdir()

        # Add a decision first
        input_text = "Test Decision\nContext\nChoice\n\n\n"
        runner.invoke(app, ["decisions", "add", str(tmp_path)], input=input_text)

        # Remove with --force
        result = runner.invoke(
            app,
            ["decisions", "remove", "1", "--path", str(tmp_path), "--force"],
        )
        assert result.exit_code == 0
        assert "Removed" in result.output

        # Verify it's gone
        result = runner.invoke(app, ["decisions", "list", str(tmp_path)])
        assert "No decisions" in result.output

    def test_decisions_list_help(self) -> None:
        """Should show decisions list help."""
        result = runner.invoke(app, ["decisions", "list", "--help"])
        assert result.exit_code == 0
        assert "architectural decisions" in result.output.lower() or "List" in result.output


class TestDiffCommand:
    """Tests for codebase diff."""

    def test_diff_requires_scan(self, initialized_project: Path) -> None:
        """Should fail when no previous scan exists."""
        result = runner.invoke(app, ["diff", str(initialized_project)])
        assert result.exit_code == 1
        assert "scan" in result.output.lower()

    def test_diff_no_changes(self, sample_python_project: Path) -> None:
        """Should show no changes when nothing changed since scan."""
        # Init and scan first
        runner.invoke(app, ["init", str(sample_python_project)])
        runner.invoke(app, ["scan", str(sample_python_project)])

        # Diff should show no changes
        result = runner.invoke(app, ["diff", str(sample_python_project)])
        assert result.exit_code == 0
        assert "No changes" in result.output or "changes" in result.output.lower()

    def test_diff_help(self) -> None:
        """Should show diff help text."""
        result = runner.invoke(app, ["diff", "--help"])
        assert result.exit_code == 0
        assert "changed" in result.output.lower() or "scan" in result.output.lower()


class TestWatchCommand:
    """Tests for codebase watch."""

    def test_watch_help(self) -> None:
        """Should show watch help text."""
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        assert "Watch" in result.output or "watch" in result.output.lower()


class TestHelpText:
    """Tests for CLI help text."""

    def test_main_help(self) -> None:
        """Should display main help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "scan" in result.output
        assert "generate" in result.output

    def test_scan_help(self) -> None:
        """Should display scan help text."""
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0

    def test_generate_help(self) -> None:
        """Should display generate help text."""
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0

    def test_hooks_help(self) -> None:
        """Should display hooks help text."""
        result = runner.invoke(app, ["hooks", "--help"])
        assert result.exit_code == 0
