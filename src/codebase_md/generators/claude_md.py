"""CLAUDE.md generator — produces context files for Claude Code.

Generates a structured Markdown file with project overview, quick reference,
architecture, build commands, conventions, and module details.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class ClaudeMdGenerator(BaseGenerator):
    """Generator for CLAUDE.md output format.

    Produces a Markdown file optimized for Claude Code's context window,
    with clear sections for project understanding, architecture, and
    coding conventions.
    """

    format_name: ClassVar[str] = "claude"
    output_filename: ClassVar[str] = "CLAUDE.md"
    supports_sections: ClassVar[list[str]] = [
        "summary",
        "quick_reference",
        "architecture",
        "build_run",
        "conventions",
        "modules",
        "dependencies",
        "decisions",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate CLAUDE.md content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete CLAUDE.md content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# CLAUDE.md — {model.name}\n")

        # What Is This Project?
        sections.append("## What Is This Project?\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Quick Reference
        sections.append(self._build_quick_reference(model))

        # Architecture
        sections.append(self._format_architecture_section(model))

        # Build & Run
        sections.append(self._build_build_run_section(model))

        # Conventions
        sections.append(self._format_conventions_section(model))

        # Modules
        if model.modules:
            sections.append(self._format_modules_section(model))

        # Key Files
        key_files = self._format_key_files_section(model)
        if key_files:
            sections.append(key_files)

        # Dependencies
        if model.dependencies:
            sections.append(self._format_dependencies_section(model))

        # API Surface
        api = self._format_api_surface_section(model)
        if api:
            sections.append(api)

        # Git Insights
        git = self._format_git_insights_section(model)
        if git:
            sections.append(git)

        # Module Relationships
        rels = self._format_module_relationships_section(model)
        if rels:
            sections.append(rels)

        # Testing
        testing = self._format_testing_section(model)
        if testing:
            sections.append(testing)

        # Security
        security = self._format_security_section(model)
        if security:
            sections.append(security)

        # Tech Debt
        tech_debt = self._format_tech_debt_section(model)
        if tech_debt:
            sections.append(tech_debt)

        # Decisions
        if model.decisions:
            sections.append(self._format_decisions_section(model))

        return "\n".join(sections)

    def _build_quick_reference(self, model: ProjectModel) -> str:
        """Build the Quick Reference section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted quick reference section.
        """
        lines = ["## Quick Reference", ""]

        if model.architecture.entry_points:
            for ep in model.architecture.entry_points:
                lines.append(f"- **Entry point**: `{ep}`")

        if model.languages:
            lines.append(f"- **Languages**: {', '.join(model.languages)}")

        arch_type = model.architecture.architecture_type.value
        if arch_type != "unknown":
            lines.append(f"- **Architecture**: {arch_type}")

        if model.modules:
            lines.append(f"- **Modules**: {len(model.modules)}")

        if model.dependencies:
            lines.append(f"- **Dependencies**: {len(model.dependencies)}")

        if model.metadata:
            lines.append(f"- **Last scanned**: {model.metadata.scanned_at}")

        lines.append("")
        return "\n".join(lines)

    def _build_build_run_section(self, model: ProjectModel) -> str:
        """Build the Build & Run section with real or language-specific commands.

        Uses extracted build commands when available, falls back to
        language-specific defaults.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted build & run section.
        """
        lines = ["## Build & Run", ""]

        # Use real commands if available
        if model.build_commands:
            real_cmds = self._format_build_commands_section(model)
            if real_cmds:
                lines.append(real_cmds)
                return "\n".join(lines)

        # Fallback to language-specific defaults
        langs_lower = [lang.lower() for lang in model.languages]

        if "python" in langs_lower:
            lines.extend(
                [
                    "```bash",
                    "# Install in dev mode",
                    "pip install -e '.[dev]'",
                    "",
                    "# Run tests",
                    "pytest",
                    "",
                    "# Lint",
                    "ruff check .",
                    "ruff format .",
                    "```",
                ]
            )
        elif any(lang in langs_lower for lang in ("javascript", "typescript")):
            lines.extend(
                [
                    "```bash",
                    "# Install dependencies",
                    "npm install",
                    "",
                    "# Run dev server",
                    "npm run dev",
                    "",
                    "# Run tests",
                    "npm test",
                    "```",
                ]
            )
        elif "go" in langs_lower:
            lines.extend(
                [
                    "```bash",
                    "# Build",
                    "go build ./...",
                    "",
                    "# Test",
                    "go test ./...",
                    "```",
                ]
            )
        elif "rust" in langs_lower:
            lines.extend(
                [
                    "```bash",
                    "# Build",
                    "cargo build",
                    "",
                    "# Test",
                    "cargo test",
                    "```",
                ]
            )
        else:
            lines.append("_Build commands vary by project setup._")

        lines.append("")
        return "\n".join(lines)
