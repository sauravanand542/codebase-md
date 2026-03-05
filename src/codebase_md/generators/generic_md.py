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

        # Dependencies
        if model.dependencies:
            sections.append(self._format_dependencies_section(model))

        # Conventions
        sections.append(self._format_conventions_section(model))

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
