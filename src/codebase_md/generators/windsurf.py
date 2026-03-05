""".windsurfrules generator — produces context files for Windsurf AI.

Generates a rules file for Windsurf with project context, coding conventions,
architecture information, and file structure guidelines.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class WindsurfGenerator(BaseGenerator):
    """Generator for .windsurfrules output format.

    Produces a rules file optimized for Windsurf's AI coding assistant.
    Similar to .cursorrules but with Windsurf-specific structure and
    emphasis on project rules and patterns.
    """

    format_name: ClassVar[str] = "windsurf"
    output_filename: ClassVar[str] = ".windsurfrules"
    supports_sections: ClassVar[list[str]] = [
        "project_context",
        "rules",
        "architecture",
        "file_structure",
        "tech_stack",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate .windsurfrules content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete .windsurfrules content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# Windsurf Rules — {model.name}\n")

        # Project Context
        sections.append("## Project Context\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Rules
        sections.append(self._build_rules(model))

        # Architecture
        sections.append(self._format_architecture_section(model))

        # File Structure
        if model.modules:
            sections.append(self._build_file_map(model))

        # API Surface
        api = self._format_api_surface_section(model)
        if api:
            sections.append(api)

        # Tech Stack
        sections.append(self._build_stack_section(model))

        # Testing
        testing = self._format_testing_section(model)
        if testing:
            sections.append(testing)

        # Security
        security = self._format_security_section(model)
        if security:
            sections.append(security)

        return "\n".join(sections)

    def _build_rules(self, model: ProjectModel) -> str:
        """Build coding rules section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted rules section.
        """
        conv = model.conventions
        lines = ["## Rules", ""]

        lines.append("### Naming & Style")
        lines.append(f"- Naming convention: **{conv.naming.value}**")
        lines.append(f"- Import style: **{conv.import_style.value}**")
        lines.append(f"- File organization: **{conv.file_org}**")
        lines.append("")

        if conv.test_pattern:
            lines.append("### Testing")
            lines.append(f"- Test pattern: `{conv.test_pattern}`")
            lines.append("")

        if conv.patterns_used:
            lines.append("### Design Patterns")
            for pattern in conv.patterns_used:
                lines.append(f"- {pattern}")
            lines.append("")

        # Language-specific rules
        langs_lower = [lang.lower() for lang in model.languages]
        if "python" in langs_lower:
            lines.extend(
                [
                    "### Python",
                    "- Type hints on all function signatures",
                    "- Google-style docstrings on public APIs",
                    "- No bare `except:` clauses",
                    "",
                ]
            )
        if any(lang in langs_lower for lang in ("javascript", "typescript")):
            lines.extend(
                [
                    "### JavaScript/TypeScript",
                    "- Prefer `const` over `let`",
                    "- Use async/await",
                    "- Avoid `any` type where possible",
                    "",
                ]
            )

        return "\n".join(lines)

    def _build_file_map(self, model: ProjectModel) -> str:
        """Build file structure map.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted file map section.
        """
        lines = ["## File Structure", ""]
        for mod in model.modules:
            purpose = f" — {mod.purpose}" if mod.purpose else ""
            lang = f" [{mod.language}]" if mod.language else ""
            lines.append(f"- `{mod.path}/`{purpose}{lang}")
        lines.append("")
        return "\n".join(lines)

    def _build_stack_section(self, model: ProjectModel) -> str:
        """Build technology stack section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted tech stack section.
        """
        lines = ["## Tech Stack", ""]
        if model.languages:
            lines.append(f"- **Languages:** {', '.join(model.languages)}")

        if model.dependencies:
            # Group by ecosystem
            ecosystems: dict[str, list[str]] = {}
            for dep in model.dependencies:
                eco = dep.ecosystem
                if eco not in ecosystems:
                    ecosystems[eco] = []
                ecosystems[eco].append(dep.name)

            for eco, names in ecosystems.items():
                display_names = names[:10]
                suffix = f" (+{len(names) - 10} more)" if len(names) > 10 else ""
                lines.append(f"- **{eco}:** {', '.join(display_names)}{suffix}")

        lines.append("")
        return "\n".join(lines)
