"""codex.md generator — produces context files for OpenAI Codex CLI.

Generates a simpler Markdown file optimized for Codex CLI's context
consumption, focusing on project setup, structure, and conventions.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class CodexMdGenerator(BaseGenerator):
    """Generator for codex.md output format.

    Produces a Markdown file optimized for OpenAI's Codex CLI tool.
    Uses a simpler, more direct structure focusing on project setup,
    coding patterns, and key reference information.
    """

    format_name: ClassVar[str] = "codex"
    output_filename: ClassVar[str] = "codex.md"
    supports_sections: ClassVar[list[str]] = [
        "summary",
        "setup",
        "structure",
        "conventions",
        "dependencies",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate codex.md content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete codex.md content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# codex.md — {model.name}\n")

        # Overview
        sections.append("## Overview\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Setup
        sections.append(self._build_setup_section(model))

        # Project Structure
        sections.append(self._build_project_structure(model))

        # Conventions
        sections.append(self._format_conventions_section(model))

        # API Surface
        api = self._format_api_surface_section(model)
        if api:
            sections.append(api)

        # Dependencies (compact)
        if model.dependencies:
            sections.append(self._build_compact_deps(model))

        # Testing
        testing = self._format_testing_section(model)
        if testing:
            sections.append(testing)

        return "\n".join(sections)

    def _build_setup_section(self, model: ProjectModel) -> str:
        """Build setup instructions section.

        Uses extracted build commands when available.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted setup section.
        """
        lines = ["## Setup", ""]

        # Use real commands if available
        if model.build_commands:
            real_cmds = self._format_build_commands_section(model)
            if real_cmds:
                lines.append(real_cmds)
                return "\n".join(lines)

        lines.append("```bash")
        langs_lower = [lang.lower() for lang in model.languages]

        if "python" in langs_lower:
            lines.extend(
                [
                    "pip install -e '.[dev]'",
                    "pytest",
                    "ruff check .",
                ]
            )
        elif any(lang in langs_lower for lang in ("javascript", "typescript")):
            lines.extend(
                [
                    "npm install",
                    "npm run dev",
                    "npm test",
                ]
            )
        elif "go" in langs_lower:
            lines.extend(
                [
                    "go build ./...",
                    "go test ./...",
                ]
            )
        elif "rust" in langs_lower:
            lines.extend(
                [
                    "cargo build",
                    "cargo test",
                ]
            )
        else:
            lines.append("# See project README for setup instructions")

        lines.extend(["```", ""])
        return "\n".join(lines)

    def _build_project_structure(self, model: ProjectModel) -> str:
        """Build project structure section with module detail.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted project structure section.
        """
        arch = model.architecture
        lines = ["## Project Structure", ""]
        lines.append(f"- **Architecture:** {arch.architecture_type.value}")

        if arch.entry_points:
            lines.append(f"- **Entry points:** {', '.join(f'`{ep}`' for ep in arch.entry_points)}")

        if model.modules:
            lines.append("")
            lines.append("**Modules:**")
            for mod in model.modules:
                purpose = f" — {mod.purpose}" if mod.purpose else ""
                file_count = f" ({len(mod.files)} files)" if mod.files else ""
                lines.append(f"- `{mod.path}`{purpose}{file_count}")

        lines.append("")
        return "\n".join(lines)

    def _build_compact_deps(self, model: ProjectModel) -> str:
        """Build compact dependencies section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted compact dependencies section.
        """
        lines = ["## Dependencies", ""]
        dep_names = [f"{dep.name} ({dep.version})" for dep in model.dependencies[:15]]
        lines.append(", ".join(dep_names))
        if len(model.dependencies) > 15:
            lines.append(f"\n_...and {len(model.dependencies) - 15} more._")
        lines.append("")
        return "\n".join(lines)
