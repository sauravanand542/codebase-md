"""Generic markdown generator — produces a tool-agnostic context file.

Generates a clean, comprehensive Markdown file suitable for any AI coding
tool's system prompt or context window. Includes all available project
information in a well-structured format.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class GenericMdGenerator(BaseGenerator):
    """Generator for generic markdown output format.

    Produces a comprehensive, tool-agnostic Markdown file that works
    with any AI coding assistant. Includes all available project
    information in a clean, structured format.
    """

    format_name: ClassVar[str] = "generic"
    output_filename: ClassVar[str] = "PROJECT_CONTEXT.md"
    supports_sections: ClassVar[list[str]] = [
        "summary",
        "languages",
        "architecture",
        "modules",
        "dependencies",
        "conventions",
        "decisions",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate generic markdown content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete generic markdown content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# Project Context — {model.name}\n")

        # Summary
        sections.append("## Summary\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Languages
        if model.languages:
            sections.append(self._format_languages_section(model))

        # Architecture
        sections.append(self._format_architecture_section(model))

        # Modules
        if model.modules:
            sections.append(self._format_modules_section(model))

        # Key Files
        key_files = self._format_key_files_section(model)
        if key_files:
            sections.append(key_files)

        # Module Relationships
        rels = self._format_module_relationships_section(model)
        if rels:
            sections.append(rels)

        # Dependencies
        if model.dependencies:
            sections.append(self._format_dependencies_section(model))

        # API Surface
        api = self._format_api_surface_section(model)
        if api:
            sections.append(api)

        # Conventions
        sections.append(self._format_conventions_section(model))

        # Git Insights
        git = self._format_git_insights_section(model)
        if git:
            sections.append(git)

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

        # Metadata
        if model.metadata:
            sections.append(self._build_metadata_section(model))

        return "\n".join(sections)

    def _build_metadata_section(self, model: ProjectModel) -> str:
        """Build metadata section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted metadata section.
        """
        if not model.metadata:
            return ""
        meta = model.metadata
        lines = ["## Scan Metadata", ""]
        lines.append(f"- **Scanned at:** {meta.scanned_at}")
        lines.append(f"- **Tool version:** {meta.version}")
        if meta.git_sha:
            lines.append(f"- **Git SHA:** `{meta.git_sha}`")
        lines.append(f"- **Scan duration:** {meta.scan_duration}s")
        lines.append("")
        return "\n".join(lines)
