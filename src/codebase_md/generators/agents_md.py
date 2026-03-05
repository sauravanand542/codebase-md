"""AGENTS.md generator — produces a cross-tool universal context file.

Generates a concise Markdown file with project summary, entry points,
key commands, conventions, and architecture flow — designed to work
with any AI coding tool.
"""

from __future__ import annotations

from typing import ClassVar

from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class AgentsMdGenerator(BaseGenerator):
    """Generator for AGENTS.md output format.

    Produces a concise, cross-tool universal Markdown file that any
    AI coding agent can consume. Focuses on actionable information:
    entry points, commands, conventions, and architecture flow.
    """

    format_name: ClassVar[str] = "agents"
    output_filename: ClassVar[str] = "AGENTS.md"
    supports_sections: ClassVar[list[str]] = [
        "summary",
        "entry_points",
        "commands",
        "conventions",
        "architecture_flow",
        "modules",
    ]

    def generate(self, model: ProjectModel) -> str:
        """Generate AGENTS.md content from the ProjectModel.

        Args:
            model: The scanned project model.

        Returns:
            Complete AGENTS.md content as a string.
        """
        sections: list[str] = []

        # Header
        sections.append(f"# AGENTS.md — {model.name}\n")

        # Project Summary
        sections.append("## Project Summary\n")
        sections.append(self._format_project_summary(model))
        sections.append("")

        # Entry Points
        sections.append(self._build_entry_points(model))

        # Key Commands
        sections.append(self._build_key_commands(model))

        # Conventions
        sections.append(self._build_compact_conventions(model))

        # Architecture Flow
        sections.append(self._build_architecture_flow(model))

        # Modules (compact)
        if model.modules:
            sections.append(self._build_compact_modules(model))

        # API Surface
        api = self._format_api_surface_section(model)
        if api:
            sections.append(api)

        # Key Files
        key_files = self._format_key_files_section(model)
        if key_files:
            sections.append(key_files)

        # Git Insights
        git = self._format_git_insights_section(model)
        if git:
            sections.append(git)

        # Testing
        testing = self._format_testing_section(model)
        if testing:
            sections.append(testing)

        # Build Status
        sections.append("## Build Status\n")
        sections.append("See `docs/progress.md` for current implementation state.")
        sections.append("")

        return "\n".join(sections)

    def _build_entry_points(self, model: ProjectModel) -> str:
        """Build entry points section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted entry points section.
        """
        lines = ["## Entry Points", ""]
        if model.architecture.entry_points:
            for ep in model.architecture.entry_points:
                lines.append(f"- `{ep}`")
        else:
            lines.append("_No entry points detected._")
        lines.append("")
        return "\n".join(lines)

    def _build_key_commands(self, model: ProjectModel) -> str:
        """Build key commands section with real or language-specific defaults.

        Uses extracted build commands when available.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted key commands section.
        """
        lines = ["## Key Commands", "", "```bash"]

        # Use real commands if available
        if model.build_commands:
            for cmd in model.build_commands:
                lines.append(cmd)
            lines.extend(["```", ""])
            return "\n".join(lines)

        # Fallback to language-specific defaults
        langs_lower = [lang.lower() for lang in model.languages]

        if "python" in langs_lower:
            lines.extend(
                [
                    "pip install -e '.[dev]'  # Install",
                    "pytest                   # Test",
                    "ruff check .             # Lint",
                    "mypy src/                # Type check",
                ]
            )
        elif any(lang in langs_lower for lang in ("javascript", "typescript")):
            lines.extend(
                [
                    "npm install              # Install",
                    "npm run dev              # Dev server",
                    "npm test                 # Test",
                    "npm run lint             # Lint",
                ]
            )
        elif "go" in langs_lower:
            lines.extend(
                [
                    "go build ./...           # Build",
                    "go test ./...            # Test",
                    "go vet ./...             # Vet",
                ]
            )
        elif "rust" in langs_lower:
            lines.extend(
                [
                    "cargo build              # Build",
                    "cargo test               # Test",
                    "cargo clippy             # Lint",
                ]
            )
        else:
            lines.append("# Build commands vary by project setup")

        lines.extend(["```", ""])
        return "\n".join(lines)

    def _build_compact_conventions(self, model: ProjectModel) -> str:
        """Build compact conventions section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted conventions section.
        """
        conv = model.conventions
        lines = ["## Conventions", ""]
        lines.append(
            f"- {conv.naming.value}, {conv.import_style.value} imports, "
            f"{conv.file_org} file organization"
        )
        if conv.test_pattern:
            lines.append(f"- Tests: `{conv.test_pattern}`")
        if conv.patterns_used:
            lines.append(f"- Patterns: {', '.join(conv.patterns_used)}")
        lines.append("")
        return "\n".join(lines)

    def _build_architecture_flow(self, model: ProjectModel) -> str:
        """Build architecture flow diagram.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted architecture flow section.
        """
        arch = model.architecture
        lines = ["## Architecture Flow", ""]
        lines.append(f"**Type:** {arch.architecture_type.value}")
        lines.append("")

        # Simple flow diagram
        lines.append("```")
        if arch.entry_points:
            entry = arch.entry_points[0]
            lines.append(f"Entry ({entry})")
        else:
            lines.append("Entry")

        if model.modules:
            mod_names = [m.name for m in model.modules[:5]]
            lines.append(f"  → Modules: {', '.join(mod_names)}")

        infra_parts: list[str] = []
        if arch.has_frontend:
            infra_parts.append("Frontend")
        if arch.has_backend:
            infra_parts.append("Backend")
        if arch.has_database:
            infra_parts.append("Database")
        if infra_parts:
            lines.append(f"  → {' + '.join(infra_parts)}")

        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    def _build_compact_modules(self, model: ProjectModel) -> str:
        """Build compact modules section.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted compact modules section.
        """
        lines = ["## Modules", ""]
        for mod in model.modules:
            purpose = f" — {mod.purpose}" if mod.purpose else ""
            lines.append(f"- `{mod.path}`{purpose}")
        lines.append("")
        return "\n".join(lines)
