"""Tests for codebase_md.generators — all output format generators."""

from __future__ import annotations

import pytest

from codebase_md.generators import AVAILABLE_FORMATS, get_generator, get_registry
from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class TestGeneratorRegistry:
    """Tests for the generator registry."""

    def test_available_formats(self) -> None:
        """Should list all 6 formats."""
        assert len(AVAILABLE_FORMATS) == 6
        assert "claude" in AVAILABLE_FORMATS
        assert "cursor" in AVAILABLE_FORMATS
        assert "agents" in AVAILABLE_FORMATS
        assert "codex" in AVAILABLE_FORMATS
        assert "windsurf" in AVAILABLE_FORMATS
        assert "generic" in AVAILABLE_FORMATS

    def test_get_generator_returns_class(self) -> None:
        """Should return a generator class for valid format name."""
        gen_class = get_generator("claude")
        assert issubclass(gen_class, BaseGenerator)

    def test_get_generator_unknown_format(self) -> None:
        """Should raise KeyError for unknown format."""
        with pytest.raises(KeyError, match="Unknown generator format"):
            get_generator("nonexistent")

    def test_registry_has_all_formats(self) -> None:
        """Should have all available formats in registry."""
        registry = get_registry()
        for fmt in AVAILABLE_FORMATS:
            assert fmt in registry

    def test_each_generator_has_format_name(self) -> None:
        """Each generator should have format_name and output_filename set."""
        registry = get_registry()
        for fmt, gen_class in registry.items():
            assert gen_class.format_name == fmt
            assert gen_class.output_filename != ""


class TestClaudeMdGenerator:
    """Tests for the CLAUDE.md generator."""

    def test_generates_valid_markdown(self, sample_project_model: ProjectModel) -> None:
        """Should produce valid markdown with key sections."""
        gen = get_generator("claude")()
        output = gen.generate(sample_project_model)
        assert "# CLAUDE.md" in output
        assert "test-project" in output

    def test_contains_architecture_section(self, sample_project_model: ProjectModel) -> None:
        """Should include architecture information."""
        gen = get_generator("claude")()
        output = gen.generate(sample_project_model)
        assert "Architecture" in output or "architecture" in output

    def test_contains_dependencies(self, sample_project_model: ProjectModel) -> None:
        """Should include dependency information."""
        gen = get_generator("claude")()
        output = gen.generate(sample_project_model)
        assert "typer" in output

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("claude")
        assert gen_class.output_filename == "CLAUDE.md"


class TestCursorRulesGenerator:
    """Tests for the .cursorrules generator."""

    def test_generates_content(self, sample_project_model: ProjectModel) -> None:
        """Should produce non-empty output."""
        gen = get_generator("cursor")()
        output = gen.generate(sample_project_model)
        assert len(output) > 0
        assert "test-project" in output

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("cursor")
        assert gen_class.output_filename == ".cursorrules"


class TestAgentsMdGenerator:
    """Tests for the AGENTS.md generator."""

    def test_generates_content(self, sample_project_model: ProjectModel) -> None:
        """Should produce AGENTS.md content."""
        gen = get_generator("agents")()
        output = gen.generate(sample_project_model)
        assert "AGENTS.md" in output or "agents" in output.lower()

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("agents")
        assert gen_class.output_filename == "AGENTS.md"


class TestCodexMdGenerator:
    """Tests for the codex.md generator."""

    def test_generates_content(self, sample_project_model: ProjectModel) -> None:
        """Should produce codex.md content."""
        gen = get_generator("codex")()
        output = gen.generate(sample_project_model)
        assert len(output) > 0

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("codex")
        assert gen_class.output_filename == "codex.md"


class TestWindsurfGenerator:
    """Tests for the .windsurfrules generator."""

    def test_generates_content(self, sample_project_model: ProjectModel) -> None:
        """Should produce .windsurfrules content."""
        gen = get_generator("windsurf")()
        output = gen.generate(sample_project_model)
        assert len(output) > 0

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("windsurf")
        assert gen_class.output_filename == ".windsurfrules"


class TestGenericMdGenerator:
    """Tests for the PROJECT_CONTEXT.md generator."""

    def test_generates_content(self, sample_project_model: ProjectModel) -> None:
        """Should produce generic markdown content."""
        gen = get_generator("generic")()
        output = gen.generate(sample_project_model)
        assert "test-project" in output

    def test_output_filename(self) -> None:
        """Should have correct output filename."""
        gen_class = get_generator("generic")
        assert gen_class.output_filename == "PROJECT_CONTEXT.md"


class TestAllGeneratorsProduceOutput:
    """Ensure every generator produces non-empty output."""

    @pytest.mark.parametrize("fmt", AVAILABLE_FORMATS)
    def test_generates_nonempty_output(
        self, fmt: str, sample_project_model: ProjectModel
    ) -> None:
        """Each generator should produce non-empty output."""
        gen = get_generator(fmt)()
        output = gen.generate(sample_project_model)
        assert isinstance(output, str)
        assert len(output) > 50  # Should be substantial output

    @pytest.mark.parametrize("fmt", AVAILABLE_FORMATS)
    def test_generates_for_minimal_model(self, fmt: str) -> None:
        """Each generator should handle minimal ProjectModel."""
        model = ProjectModel(name="minimal", root_path="/tmp/min")
        gen = get_generator(fmt)()
        output = gen.generate(model)
        assert isinstance(output, str)
        assert len(output) > 0
