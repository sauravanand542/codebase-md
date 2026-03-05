""".cursorrules generator — produces context files for Cursor AI.

Generates a Markdown file with coding rules, conventions, project structure,
and patterns that Cursor uses for inline AI assistance.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class CursorRulesGenerator(BaseGenerator):
    """Generator for .cursorrules output format.

    Produces a file optimized for Cursor's rules system, emphasizing
    coding conventions, naming patterns, file structure, and project-specific
    guidelines that Cursor should follow when generating code.
    """

    format_name: ClassVar[str] = "cursor"
    output_filename: ClassVar[str] = ".cursorrules"
    supports_sections: ClassVar[list[str]] = [
        "project_context",
        "conventions",
        "architecture",
        "patterns",
        "file_structure",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate .cursorrules content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete .cursorrules content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# Project: {model.name}\n")

        # Project Context
        sections.append("## Project Context\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Coding Conventions (primary focus for Cursor)
        sections.append(self._build_coding_rules(model))

        # Architecture & Structure
        sections.append(self._build_structure_rules(model))

        # File Patterns
        if model.modules:
            sections.append(self._build_file_patterns(model))

        # Technology Stack
        sections.append(self._build_tech_stack(model))

        return "\n".join(sections)

    def _build_coding_rules(self, model: ProjectModel) -> str:
        """Build coding rules section focused on conventions.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted coding rules.
        """
        conv = model.conventions
        lines = ["## Coding Rules", ""]
        lines.append(f"- Use **{conv.naming.value}** naming convention")
        lines.append(f"- Use **{conv.import_style.value}** imports")
        lines.append(f"- File organization: **{conv.file_org}**")

        if conv.test_pattern:
            lines.append(f"- Test files follow pattern: `{conv.test_pattern}`")

        if conv.patterns_used:
            lines.append(f"- Design patterns in use: {', '.join(conv.patterns_used)}")

        # Language-specific rules
        langs_lower = [lang.lower() for lang in model.languages]
        if "python" in langs_lower:
            lines.extend(
                [
                    "",
                    "### Python Rules",
                    "- All function signatures must have type hints",
                    "- Use Google-style docstrings on all public functions and classes",
                    "- Never use bare `except:`",
                ]
            )
        if any(lang in langs_lower for lang in ("javascript", "typescript")):
            lines.extend(
                [
                    "",
                    "### JavaScript/TypeScript Rules",
                    "- Prefer `const` over `let`, avoid `var`",
                    "- Use async/await over raw promises where possible",
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def _build_structure_rules(self, model: ProjectModel) -> str:
        """Build architecture and structure rules.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted structure rules.
        """
        arch = model.architecture
        lines = ["## Architecture", ""]
        lines.append(f"- **Type:** {arch.architecture_type.value}")

        if arch.entry_points:
            lines.append(f"- **Entry points:** {', '.join(f'`{ep}`' for ep in arch.entry_points)}")

        infra: list[str] = []
        if arch.has_frontend:
            infra.append("Frontend")
        if arch.has_backend:
            infra.append("Backend")
        if arch.has_database:
            infra.append("Database")
        if arch.has_docker:
            infra.append("Docker")
        if arch.has_ci:
            infra.append("CI/CD")
        if infra:
            lines.append(f"- **Infrastructure:** {', '.join(infra)}")

        lines.append("")
        return "\n".join(lines)

    def _build_file_patterns(self, model: ProjectModel) -> str:
        """Build file patterns section showing module layout.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted file patterns.
        """
        lines = ["## File Structure", ""]
        lines.append("```")
        for mod in model.modules:
            purpose = f"  # {mod.purpose}" if mod.purpose else ""
            lines.append(f"{mod.path}/{purpose}")
            if mod.files:
                for f in mod.files[:10]:  # Limit to 10 files per module
                    lines.append(f"  {f.path}")
                if len(mod.files) > 10:
                    lines.append(f"  ... and {len(mod.files) - 10} more files")
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    def _build_tech_stack(self, model: ProjectModel) -> str:
        """Build technology stack section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted tech stack.
        """
        lines = ["## Tech Stack", ""]
        if model.languages:
            lines.append(f"- **Languages:** {', '.join(model.languages)}")
        if model.dependencies:
            dep_names = [dep.name for dep in model.dependencies[:20]]
            lines.append(f"- **Key packages:** {', '.join(dep_names)}")
            if len(model.dependencies) > 20:
                lines.append(f"  _(and {len(model.dependencies) - 20} more)_")
        lines.append("")
        return "\n".join(lines)
