"""Abstract base generator interface for all output formats.

Every generator inherits from BaseGenerator and implements the
generate() method to transform a ProjectModel into format-specific text.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from codebase_md.model.project import ProjectModel


class GeneratorError(Exception):
    """Base exception for generator operations."""


class BaseGenerator(ABC):
    """Abstract base class for output format generators.

    Each subclass transforms a ProjectModel into a specific output format
    (CLAUDE.md, .cursorrules, AGENTS.md, etc.). Generators are stateless —
    all data comes from the ProjectModel.

    Class Attributes:
        format_name: Short identifier for the format (e.g. 'claude', 'cursor').
        output_filename: Name of the file to write (e.g. 'CLAUDE.md', '.cursorrules').
        supports_sections: List of section identifiers this format supports.
    """

    format_name: ClassVar[str] = ""
    output_filename: ClassVar[str] = ""
    supports_sections: ClassVar[list[str]] = []

    @abstractmethod
    def generate(self, model: ProjectModel) -> str:
        """Generate the output content from a ProjectModel.

        Args:
            model: The scanned project model containing all project data.

        Returns:
            The generated content as a string, ready to write to a file.

        Raises:
            GeneratorError: If generation fails due to missing or invalid data.
        """

    # ------------------------------------------------------------------
    # Shared helper methods for building common sections
    # ------------------------------------------------------------------

    def _format_project_summary(self, model: ProjectModel) -> str:
        """Build a one-paragraph project summary.

        Args:
            model: The project model.

        Returns:
            A summary string describing the project.
        """
        parts: list[str] = [f"`{model.name}`"]

        if model.languages:
            lang_str = ", ".join(model.languages)
            parts.append(f"built with {lang_str}")

        arch = model.architecture.architecture_type.value
        if arch != "unknown":
            parts.append(f"({arch} architecture)")

        if model.modules:
            parts.append(f"with {len(model.modules)} module(s)")

        if model.dependencies:
            parts.append(f"and {len(model.dependencies)} dependencies")

        return " ".join(parts) + "."

    def _format_languages_section(self, model: ProjectModel) -> str:
        """Build a languages section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted languages section.
        """
        if not model.languages:
            return ""
        lines = ["## Languages", ""]
        for lang in model.languages:
            lines.append(f"- {lang}")
        lines.append("")
        return "\n".join(lines)

    def _format_architecture_section(self, model: ProjectModel) -> str:
        """Build an architecture section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted architecture section.
        """
        arch = model.architecture
        lines = ["## Architecture", ""]
        lines.append(f"**Type:** {arch.architecture_type.value}")
        lines.append("")

        if arch.entry_points:
            lines.append("**Entry Points:**")
            for ep in arch.entry_points:
                lines.append(f"- `{ep}`")
            lines.append("")

        if arch.services:
            lines.append("**Services:**")
            for svc in arch.services:
                desc = svc.name
                if svc.framework:
                    desc += f" ({svc.framework})"
                if svc.language:
                    desc += f" [{svc.language}]"
                lines.append(f"- `{svc.path}` — {desc}")
            lines.append("")

        # Infrastructure markers
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
            lines.append(f"**Infrastructure:** {', '.join(infra)}")
            lines.append("")

        return "\n".join(lines)

    def _format_modules_section(self, model: ProjectModel) -> str:
        """Build a modules section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted modules section.
        """
        if not model.modules:
            return ""
        lines = ["## Modules", ""]
        for mod in model.modules:
            header = f"### {mod.name}"
            if mod.framework:
                header += f" ({mod.framework})"
            lines.append(header)
            if mod.purpose:
                lines.append(f"{mod.purpose}")
            lines.append(f"- **Path:** `{mod.path}`")
            if mod.language:
                lines.append(f"- **Language:** {mod.language}")
            if mod.files:
                lines.append(f"- **Files:** {len(mod.files)}")
            lines.append("")
        return "\n".join(lines)

    def _format_dependencies_section(self, model: ProjectModel) -> str:
        """Build a dependencies section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted dependencies section.
        """
        if not model.dependencies:
            return ""
        lines = ["## Dependencies", ""]
        lines.append("| Package | Version | Ecosystem |")
        lines.append("|---------|---------|-----------|")
        for dep in model.dependencies:
            lines.append(f"| {dep.name} | {dep.version} | {dep.ecosystem} |")
        lines.append("")
        return "\n".join(lines)

    def _format_conventions_section(self, model: ProjectModel) -> str:
        """Build a conventions section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted conventions section.
        """
        conv = model.conventions
        lines = ["## Conventions", ""]
        lines.append(f"- **Naming:** {conv.naming.value}")
        lines.append(f"- **File Organization:** {conv.file_org}")
        lines.append(f"- **Import Style:** {conv.import_style.value}")
        if conv.test_pattern:
            lines.append(f"- **Test Pattern:** `{conv.test_pattern}`")
        if conv.patterns_used:
            lines.append(f"- **Patterns:** {', '.join(conv.patterns_used)}")
        lines.append("")
        return "\n".join(lines)

    def _format_decisions_section(self, model: ProjectModel) -> str:
        """Build a decisions section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted decisions section.
        """
        if not model.decisions:
            return ""
        lines = ["## Decisions", ""]
        for dec in model.decisions:
            lines.append(f"### {dec.title}")
            if dec.date:
                lines.append(f"**Date:** {dec.date}")
            if dec.context:
                lines.append(f"**Context:** {dec.context}")
            lines.append(f"**Choice:** {dec.choice}")
            if dec.alternatives:
                lines.append(f"**Alternatives:** {', '.join(dec.alternatives)}")
            if dec.consequences:
                lines.append(f"**Consequences:** {', '.join(dec.consequences)}")
            lines.append("")
        return "\n".join(lines)
