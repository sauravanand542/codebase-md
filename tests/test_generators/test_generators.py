"""Tests for codebase_md.generators — all output format generators."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from codebase_md.generators import AVAILABLE_FORMATS, get_generator, get_registry
from codebase_md.generators.base import BaseGenerator
from codebase_md.model.architecture import ArchitectureInfo, ArchitectureType
from codebase_md.model.convention import ConventionSet, ImportStyle, NamingConvention
from codebase_md.model.dependency import DependencyInfo
from codebase_md.model.module import APIEndpoint, FileInfo, ModuleInfo
from codebase_md.model.project import GitInsights, ProjectModel


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
    def test_generates_nonempty_output(self, fmt: str, sample_project_model: ProjectModel) -> None:
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


# ──────────────────────────────────────────────────────────────────────
# Phase 8D — Generator Enrichment Tests
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def enriched_model() -> ProjectModel:
    """A richly populated model for enrichment tests."""
    return ProjectModel(
        name="enriched-app",
        description="A powerful codebase scanner for AI context generation.",
        root_path="/tmp/enriched",
        languages=["python", "typescript"],
        build_commands=["pytest", "ruff check .", "npm run build"],
        architecture=ArchitectureInfo(
            architecture_type=ArchitectureType.MONOLITH,
            entry_points=["src/main.py"],
            has_backend=True,
            has_ci=True,
        ),
        modules=[
            ModuleInfo(
                name="core",
                path="src/core",
                purpose="Core scanning engine",
                language="python",
                files=[
                    FileInfo(
                        path="src/core/engine.py",
                        language="python",
                        exports=["scan_project", "ScanResult", "ScannerError"],
                        imports=["pathlib", "codebase_md.model"],
                        purpose="Scanner orchestration",
                    ),
                    FileInfo(
                        path="src/core/detector.py",
                        language="python",
                        exports=["detect_languages", "LanguageInfo"],
                        imports=["pathlib", "re"],
                        purpose="Language detection",
                    ),
                ],
            ),
            ModuleInfo(
                name="generators",
                path="src/generators",
                purpose="Output format generators",
                language="python",
                files=[
                    FileInfo(
                        path="src/generators/claude.py",
                        language="python",
                        exports=["ClaudeMdGenerator"],
                        imports=["codebase_md.generators.base", "codebase_md.model"],
                        purpose="CLAUDE.md generator",
                    ),
                ],
            ),
        ],
        dependencies=[
            DependencyInfo(
                name="typer",
                version=">=0.9.0",
                ecosystem="pypi",
                dep_type="runtime",
            ),
            DependencyInfo(
                name="pytest",
                version=">=7.0.0",
                ecosystem="pypi",
                dep_type="dev",
            ),
            DependencyInfo(
                name="tree-sitter",
                version=">=0.21.0",
                ecosystem="pypi",
                dep_type="optional",
            ),
        ],
        conventions=ConventionSet(
            naming=NamingConvention.SNAKE_CASE,
            file_org="modular",
            import_style=ImportStyle.ABSOLUTE,
            test_pattern="test_*.py",
            patterns_used=["model", "service"],
        ),
        tech_debt=["Needs error handling cleanup"],
        security=["Input validation on file paths"],
        testing=["pytest", "85% coverage", "integration tests"],
        api_surface=[
            APIEndpoint(
                method="GET",
                path="/api/health",
                handler="routes.health_check",
                auth_required=False,
            ),
            APIEndpoint(
                method="POST",
                path="/api/scan",
                handler="routes.start_scan",
                auth_required=True,
            ),
        ],
        git_insights=GitInsights(
            total_commits=250,
            contributors=["Alice", "Bob", "Charlie"],
            hotspots=["src/core/engine.py", "src/generators/claude.py"],
            recent_files=["src/core/engine.py"],
            branch="main",
        ),
    )


class TestProjectDescription:
    """Tests for project description rendering (P0 #1)."""

    def test_description_in_claude_output(self, enriched_model: ProjectModel) -> None:
        """Claude output should use project description."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "A powerful codebase scanner" in output

    def test_description_in_agents_output(self, enriched_model: ProjectModel) -> None:
        """AGENTS output should use project description."""
        gen = get_generator("agents")()
        output = gen.generate(enriched_model)
        assert "A powerful codebase scanner" in output

    @pytest.mark.parametrize("fmt", AVAILABLE_FORMATS)
    def test_description_appears_in_all_formats(
        self, fmt: str, enriched_model: ProjectModel
    ) -> None:
        """Project description should appear in all generator output."""
        gen = get_generator(fmt)()
        output = gen.generate(enriched_model)
        assert "A powerful codebase scanner" in output

    def test_fallback_summary_when_no_description(self) -> None:
        """Without description, should fall back to skeleton summary."""
        model = ProjectModel(
            name="bare",
            root_path="/tmp/bare",
            languages=["python"],
        )
        gen = get_generator("claude")()
        output = gen.generate(model)
        assert "`bare`" in output
        assert "python" in output


class TestRichModuleDetails:
    """Tests for rich module rendering with files (P0 #2)."""

    def test_key_files_shown_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show key files with purpose."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "engine.py" in output
        assert "Scanner orchestration" in output

    def test_exports_shown_in_modules(self, enriched_model: ProjectModel) -> None:
        """Module section should show file exports."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "scan_project" in output

    def test_generic_has_key_files(self, enriched_model: ProjectModel) -> None:
        """Generic output should include key files section."""
        gen = get_generator("generic")()
        output = gen.generate(enriched_model)
        assert "Key Files" in output


class TestRealBuildCommands:
    """Tests for real build commands (P1 #4)."""

    def test_real_commands_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should use extracted build commands."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "pytest" in output
        assert "ruff check" in output

    def test_real_commands_in_agents(self, enriched_model: ProjectModel) -> None:
        """AGENTS output should use extracted build commands."""
        gen = get_generator("agents")()
        output = gen.generate(enriched_model)
        assert "pytest" in output

    def test_real_commands_in_codex(self, enriched_model: ProjectModel) -> None:
        """Codex output should use extracted build commands."""
        gen = get_generator("codex")()
        output = gen.generate(enriched_model)
        assert "pytest" in output

    def test_fallback_when_no_commands(self) -> None:
        """Without build_commands, should fall back to language defaults."""
        model = ProjectModel(
            name="no-cmds",
            root_path="/tmp/no-cmds",
            languages=["python"],
        )
        gen = get_generator("claude")()
        output = gen.generate(model)
        assert "pip install" in output


class TestAPISurfaceRendering:
    """Tests for API surface rendering (P1 #5)."""

    def test_api_table_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show API endpoint table."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "API Surface" in output
        assert "/api/health" in output
        assert "GET" in output

    def test_api_auth_marker(self, enriched_model: ProjectModel) -> None:
        """API table should show auth requirement markers."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        # POST /api/scan has auth_required=True → ✓
        assert "✓" in output

    def test_api_in_generic(self, enriched_model: ProjectModel) -> None:
        """Generic output should include API surface."""
        gen = get_generator("generic")()
        output = gen.generate(enriched_model)
        assert "API Surface" in output

    def test_no_api_section_when_empty(self) -> None:
        """Should not render API section if no endpoints."""
        model = ProjectModel(name="no-api", root_path="/tmp")
        gen = get_generator("claude")()
        output = gen.generate(model)
        assert "API Surface" not in output


class TestDependencyCategorization:
    """Tests for dependency type grouping (P1 #6)."""

    def test_deps_grouped_by_type(self, enriched_model: ProjectModel) -> None:
        """Dependencies should be grouped by type."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Runtime" in output or "Development" in output or "Optional" in output

    def test_dep_type_field_exists(self) -> None:
        """DependencyInfo should have dep_type field."""
        dep = DependencyInfo(name="foo", version="1.0", ecosystem="pypi", dep_type="dev")
        assert dep.dep_type == "dev"

    def test_dep_type_default_is_runtime(self) -> None:
        """Default dep_type should be 'runtime'."""
        dep = DependencyInfo(name="bar", version="1.0", ecosystem="pypi")
        assert dep.dep_type == "runtime"


class TestConventionExamples:
    """Tests for convention examples from code (P2 #8)."""

    def test_convention_examples_shown(self, enriched_model: ProjectModel) -> None:
        """Convention section should show real code examples."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        # Should show actual exports as convention examples
        assert "Examples from codebase" in output

    def test_function_examples(self, enriched_model: ProjectModel) -> None:
        """Should identify function names as examples."""
        gen = get_generator("generic")()
        output = gen.generate(enriched_model)
        assert "scan_project" in output or "detect_languages" in output

    def test_class_examples(self, enriched_model: ProjectModel) -> None:
        """Should identify class names as examples."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        # ScanResult, ScannerError, ClaudeMdGenerator — PascalCase
        assert "ScanResult" in output or "ClaudeMdGenerator" in output


class TestGitInsights:
    """Tests for git insights section (P2 #9)."""

    def test_git_insights_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show git insights."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Git Insights" in output

    def test_hotspots_shown(self, enriched_model: ProjectModel) -> None:
        """Should show most-changed files."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Hotspot" in output or "engine.py" in output

    def test_contributors_shown(self, enriched_model: ProjectModel) -> None:
        """Should show contributors."""
        gen = get_generator("generic")()
        output = gen.generate(enriched_model)
        assert "Alice" in output

    def test_no_git_section_when_empty(self) -> None:
        """Should not render git section if no git data."""
        model = ProjectModel(name="no-git", root_path="/tmp")
        gen = get_generator("claude")()
        output = gen.generate(model)
        assert "Git Insights" not in output


class TestModuleRelationships:
    """Tests for module relationship diagram (P3 #10)."""

    def test_relationship_with_cross_module_imports(self) -> None:
        """Should show relationships when modules import from each other."""
        model = ProjectModel(
            name="rel-test",
            root_path="/tmp",
            modules=[
                ModuleInfo(
                    name="core",
                    path="src/core",
                    files=[
                        FileInfo(
                            path="src/core/engine.py",
                            exports=["scan"],
                            imports=["src/generators/base"],
                        ),
                    ],
                ),
                ModuleInfo(
                    name="generators",
                    path="src/generators",
                    files=[
                        FileInfo(
                            path="src/generators/base.py",
                            exports=["BaseGenerator"],
                            imports=[],
                        ),
                    ],
                ),
            ],
        )
        gen = get_generator("generic")()
        output = gen.generate(model)
        assert "Module Relationships" in output
        assert "core" in output and "generators" in output

    def test_no_relationships_single_module(self) -> None:
        """Should not show relationships with single module."""
        model = ProjectModel(
            name="single",
            root_path="/tmp",
            modules=[ModuleInfo(name="app", path="src")],
        )
        gen = get_generator("generic")()
        output = gen.generate(model)
        assert "Module Relationships" not in output


class TestTestingSecurityTechDebt:
    """Tests for testing/security/tech_debt sections (P3 #12)."""

    def test_testing_section_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show testing info."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Testing" in output
        assert "pytest" in output

    def test_security_section_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show security info."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Security" in output
        assert "Input validation" in output

    def test_tech_debt_in_claude(self, enriched_model: ProjectModel) -> None:
        """Claude output should show tech debt."""
        gen = get_generator("claude")()
        output = gen.generate(enriched_model)
        assert "Tech Debt" in output
        assert "error handling" in output

    def test_no_testing_when_empty(self) -> None:
        """Should not show testing section if empty."""
        model = ProjectModel(name="empty", root_path="/tmp")
        gen = get_generator("claude")()
        output = gen.generate(model)
        assert "Testing" not in output


class TestGitInsightsModel:
    """Tests for the GitInsights Pydantic model."""

    def test_git_insights_defaults(self) -> None:
        """GitInsights should have sensible defaults."""
        gi = GitInsights()
        assert gi.total_commits == 0
        assert gi.contributors == []
        assert gi.hotspots == []
        assert gi.recent_files == []
        assert gi.branch == ""

    def test_git_insights_frozen(self) -> None:
        """GitInsights should be immutable."""
        gi = GitInsights(total_commits=10)
        with pytest.raises(ValidationError):
            gi.total_commits = 20  # type: ignore[misc]


class TestScannerDescriptionExtraction:
    """Tests for scanner-level description extraction."""

    def test_readme_description_extraction(self) -> None:
        """Should extract first paragraph from README."""
        from codebase_md.scanner.engine import _extract_readme_description

        content = "# My Project\n\nThis is a cool project that does things.\n\n## Install\n"
        desc = _extract_readme_description(content)
        assert "cool project" in desc

    def test_readme_skips_badges(self) -> None:
        """Should skip badge lines in README."""
        from codebase_md.scanner.engine import _extract_readme_description

        content = (
            "# Project\n\n[![Build](http://img.shields.io/badge)]\n\nActual description here.\n"
        )
        desc = _extract_readme_description(content)
        assert "Actual description" in desc

    def test_pyproject_description(self) -> None:
        """Should extract description from pyproject.toml."""
        from codebase_md.scanner.engine import _extract_pyproject_description

        content = '[project]\nname = "foo"\ndescription = "A great tool"\n'
        desc = _extract_pyproject_description(content)
        assert "A great tool" in desc

    def test_build_git_insights(self) -> None:
        """Should build GitInsights from GitInfo."""
        from codebase_md.scanner.engine import _build_git_insights
        from codebase_md.scanner.git_analyzer import GitInfo

        gi = GitInfo(
            total_commits=42,
            contributors=["Dev1"],
            hotspots=["a.py"],
            branch="dev",
        )
        insights = _build_git_insights(gi)
        assert insights.total_commits == 42
        assert insights.branch == "dev"

    def test_build_git_insights_none(self) -> None:
        """Should return empty GitInsights for None input."""
        from codebase_md.scanner.engine import _build_git_insights

        insights = _build_git_insights(None)
        assert insights.total_commits == 0
