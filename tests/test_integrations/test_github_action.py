"""Tests for codebase_md.integrations.github_action."""

from __future__ import annotations

from pathlib import Path

from codebase_md.integrations.github_action import (
    ActionConfig,
    generate_workflow,
    write_workflow,
)


class TestActionConfig:
    """Tests for ActionConfig model."""

    def test_defaults(self) -> None:
        """Should have sensible defaults."""
        config = ActionConfig()
        assert config.python_version == "3.11"
        assert "push" in config.triggers
        assert "pull_request" in config.triggers
        assert config.auto_commit is False
        assert len(config.formats) == 6

    def test_custom_config(self) -> None:
        """Should accept custom values."""
        config = ActionConfig(
            python_version="3.12",
            triggers=["push"],
            branches=["main", "develop"],
            auto_commit=True,
            formats=["claude", "agents"],
        )
        assert config.python_version == "3.12"
        assert config.auto_commit is True
        assert len(config.formats) == 2


class TestGenerateWorkflow:
    """Tests for generate_workflow function."""

    def test_generates_yaml(self) -> None:
        """Should produce valid YAML-like content."""
        output = generate_workflow()
        assert "name: codebase-md" in output
        assert "jobs:" in output
        assert "steps:" in output

    def test_contains_scan_step(self) -> None:
        """Should include codebase scan step."""
        output = generate_workflow()
        assert "codebase scan" in output

    def test_contains_generate_step(self) -> None:
        """Should include codebase generate step."""
        output = generate_workflow()
        assert "codebase generate" in output

    def test_contains_python_setup(self) -> None:
        """Should include Python setup step."""
        output = generate_workflow()
        assert "Set up Python" in output
        assert "actions/setup-python" in output

    def test_contains_checkout(self) -> None:
        """Should include checkout step."""
        output = generate_workflow()
        assert "actions/checkout" in output

    def test_custom_python_version(self) -> None:
        """Should use custom Python version."""
        config = ActionConfig(python_version="3.12")
        output = generate_workflow(config)
        assert "3.12" in output

    def test_auto_commit_step(self) -> None:
        """Should include commit step when auto_commit is True."""
        config = ActionConfig(auto_commit=True)
        output = generate_workflow(config)
        assert "git commit" in output
        assert "git push" in output
        assert "contents: write" in output

    def test_no_auto_commit_by_default(self) -> None:
        """Should not include commit step by default."""
        output = generate_workflow()
        assert "git commit" not in output
        assert "contents: read" in output

    def test_workflow_dispatch_trigger(self) -> None:
        """Should support workflow_dispatch trigger."""
        config = ActionConfig(triggers=["push", "workflow_dispatch"])
        output = generate_workflow(config)
        assert "workflow_dispatch" in output

    def test_default_config(self) -> None:
        """Should work with None config (uses defaults)."""
        output = generate_workflow(None)
        assert "codebase-md" in output


class TestWriteWorkflow:
    """Tests for write_workflow function."""

    def test_writes_file(self, tmp_path: Path) -> None:
        """Should write the workflow file to disk."""
        result = write_workflow(tmp_path)
        assert result.is_file()
        assert result.name == "codebase-md.yml"

    def test_creates_directories(self, tmp_path: Path) -> None:
        """Should create .github/workflows/ if needed."""
        write_workflow(tmp_path)
        assert (tmp_path / ".github" / "workflows").is_dir()

    def test_file_content(self, tmp_path: Path) -> None:
        """Should write valid workflow content."""
        result = write_workflow(tmp_path)
        content = result.read_text()
        assert "name: codebase-md" in content
        assert "codebase scan" in content
