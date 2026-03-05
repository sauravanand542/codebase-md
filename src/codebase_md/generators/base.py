"""Abstract base generator interface for all output formats.

Every generator inherits from BaseGenerator and implements the
generate() method to transform a ProjectModel into format-specific text.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from codebase_md.model.dependency import DependencyInfo
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
        """Build a one-paragraph project summary, including description.

        Args:
            model: The project model.

        Returns:
            A summary string describing the project.
        """
        # Use real description if available
        if model.description:
            return model.description

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
        """Build a rich modules section with file details.

        Shows purpose, key files with their purpose and exports (top 10),
        instead of just a file count.

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

                # Show key files with purpose and exports
                key_files = [f for f in mod.files if f.purpose or f.exports]
                display_files = key_files[:10] if key_files else mod.files[:5]
                if display_files:
                    lines.append("")
                    lines.append("**Key Files:**")
                    for f in display_files:
                        entry = f"- `{f.path}`"
                        if f.purpose:
                            entry += f" — {f.purpose}"
                        lines.append(entry)
                        if f.exports:
                            exports_str = ", ".join(f"`{e}`" for e in f.exports[:8])
                            if len(f.exports) > 8:
                                exports_str += f" (+{len(f.exports) - 8} more)"
                            lines.append(f"  Exports: {exports_str}")
            lines.append("")
        return "\n".join(lines)

    def _format_dependencies_section(self, model: ProjectModel) -> str:
        """Build a dependencies section with type categorization.

        Groups dependencies by type (runtime, dev, optional, peer)
        and shows them in a table.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted dependencies section.
        """
        if not model.dependencies:
            return ""

        # Group by dep_type
        groups: dict[str, list[DependencyInfo]] = {}
        for dep in model.dependencies:
            dtype = getattr(dep, "dep_type", "runtime")
            groups.setdefault(dtype, []).append(dep)

        lines = ["## Dependencies", ""]

        # If all are the same type, use flat table
        if len(groups) <= 1:
            lines.append("| Package | Version | Ecosystem |")
            lines.append("|---------|---------|-----------|")
            for dep in model.dependencies:
                lines.append(f"| {dep.name} | {dep.version} | {dep.ecosystem} |")
            lines.append("")
        else:
            # Group by type
            type_labels = {
                "runtime": "Runtime",
                "dev": "Development",
                "optional": "Optional",
                "peer": "Peer",
            }
            for dtype in ("runtime", "dev", "optional", "peer"):
                deps = groups.get(dtype, [])
                if not deps:
                    continue
                label = type_labels.get(dtype, dtype.title())
                lines.append(f"### {label} Dependencies")
                lines.append("")
                lines.append("| Package | Version | Ecosystem |")
                lines.append("|---------|---------|-----------|")
                for dep in deps:
                    lines.append(f"| {dep.name} | {dep.version} | {dep.ecosystem} |")
                lines.append("")

        return "\n".join(lines)

    def _format_conventions_section(self, model: ProjectModel) -> str:
        """Build a conventions section with examples from actual code.

        Instead of just labeling the convention, shows real examples
        from AST-detected exports.

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

        # Add real examples from code
        examples = self._collect_convention_examples(model)
        if examples:
            lines.append("")
            lines.append("**Examples from codebase:**")
            for category, items in examples.items():
                items_str = ", ".join(f"`{i}`" for i in items[:5])
                lines.append(f"- {category}: {items_str}")

        lines.append("")
        return "\n".join(lines)

    def _collect_convention_examples(self, model: ProjectModel) -> dict[str, list[str]]:
        """Collect naming convention examples from AST exports.

        Scans module files for exported functions and classes
        to show real naming examples.

        Args:
            model: The project model.

        Returns:
            Dict mapping category names to lists of example names.
        """
        functions: list[str] = []
        classes: list[str] = []

        for mod in model.modules:
            for f in mod.files:
                for export in f.exports:
                    if not export:
                        continue
                    # Heuristic: PascalCase → class, else → function
                    if export[0].isupper() and "_" not in export:
                        if export not in classes:
                            classes.append(export)
                    elif export not in functions:
                        functions.append(export)

        result: dict[str, list[str]] = {}
        if functions:
            result["Functions"] = functions[:5]
        if classes:
            result["Classes"] = classes[:5]
        return result

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

    def _format_api_surface_section(self, model: ProjectModel) -> str:
        """Build an API surface section showing detected endpoints.

        Renders method, path, handler, and auth status for each endpoint.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted API surface section, or "" if no endpoints.
        """
        if not model.api_surface:
            return ""
        lines = ["## API Surface", ""]
        lines.append("| Method | Path | Handler | Auth |")
        lines.append("|--------|------|---------|------|")
        for ep in model.api_surface:
            auth = "✓" if ep.auth_required else "—"
            handler = ep.handler or "—"
            lines.append(f"| {ep.method} | `{ep.path}` | `{handler}` | {auth} |")
        lines.append("")
        return "\n".join(lines)

    def _format_key_files_section(self, model: ProjectModel) -> str:
        """Build a Key Files section showing the most important files.

        Selects files with purpose or exports across all modules,
        sorted by number of exports (most significant first).

        Args:
            model: The project model.

        Returns:
            Markdown-formatted key files section.
        """
        all_files = []
        for mod in model.modules:
            for f in mod.files:
                if f.purpose or f.exports:
                    all_files.append(f)

        if not all_files:
            return ""

        # Sort by significance: files with more exports first
        all_files.sort(key=lambda f: len(f.exports), reverse=True)
        top_files = all_files[:15]

        lines = ["## Key Files", ""]
        for f in top_files:
            entry = f"- `{f.path}`"
            if f.purpose:
                entry += f" — {f.purpose}"
            lines.append(entry)
            if f.exports:
                exports_str = ", ".join(f"`{e}`" for e in f.exports[:6])
                if len(f.exports) > 6:
                    exports_str += f" (+{len(f.exports) - 6} more)"
                lines.append(f"  Exports: {exports_str}")
            if f.imports:
                imports_str = ", ".join(f"`{i}`" for i in f.imports[:6])
                if len(f.imports) > 6:
                    imports_str += f" (+{len(f.imports) - 6} more)"
                lines.append(f"  Imports: {imports_str}")
        lines.append("")
        return "\n".join(lines)

    def _format_git_insights_section(self, model: ProjectModel) -> str:
        """Build a Git Insights section from git analysis data.

        Shows hotspots (most-changed files), recent activity,
        contributors, and commit count.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted git insights section.
        """
        gi = model.git_insights
        if not gi.total_commits and not gi.contributors:
            return ""

        lines = ["## Git Insights", ""]

        if gi.branch:
            lines.append(f"- **Branch:** `{gi.branch}`")
        if gi.total_commits:
            lines.append(f"- **Total commits:** {gi.total_commits}")
        if gi.contributors:
            contribs = ", ".join(gi.contributors[:10])
            if len(gi.contributors) > 10:
                contribs += f" (+{len(gi.contributors) - 10} more)"
            lines.append(f"- **Contributors:** {contribs}")
        lines.append("")

        if gi.hotspots:
            lines.append("**Most Changed Files (Hotspots):**")
            for hp in gi.hotspots[:10]:
                lines.append(f"- `{hp}`")
            lines.append("")

        if gi.recent_files:
            lines.append("**Recently Modified:**")
            for rf in gi.recent_files[:10]:
                lines.append(f"- `{rf}`")
            lines.append("")

        return "\n".join(lines)

    def _format_module_relationships_section(self, model: ProjectModel) -> str:
        """Build a text diagram showing inter-module dependencies.

        Derives from FileInfo imports which modules depend on which.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted relationship section.
        """
        if len(model.modules) < 2:
            return ""

        # Build module name → path mapping
        mod_paths = {mod.path: mod.name for mod in model.modules}

        # Find cross-module imports
        relationships: dict[str, set[str]] = {}
        for mod in model.modules:
            for f in mod.files:
                for imp in f.imports:
                    # Check if import references another module
                    for other_path, other_name in mod_paths.items():
                        if other_path != mod.path and (
                            imp.startswith(other_path)
                            or imp.startswith(other_name)
                            or other_name in imp
                        ):
                            relationships.setdefault(mod.name, set()).add(other_name)
                            break

        if not relationships:
            return ""

        lines = ["## Module Relationships", ""]
        lines.append("```")
        for source, targets in sorted(relationships.items()):
            for target in sorted(targets):
                lines.append(f"{source} → {target}")
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    def _format_testing_section(self, model: ProjectModel) -> str:
        """Build a testing information section.

        Renders test framework, coverage, and pattern information.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted testing section.
        """
        if not model.testing:
            return ""
        lines = ["## Testing", ""]
        for item in model.testing:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _format_security_section(self, model: ProjectModel) -> str:
        """Build a security section.

        Renders security observations and concerns.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted security section.
        """
        if not model.security:
            return ""
        lines = ["## Security", ""]
        for item in model.security:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _format_tech_debt_section(self, model: ProjectModel) -> str:
        """Build a tech debt section.

        Renders identified tech debt items.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted tech debt section.
        """
        if not model.tech_debt:
            return ""
        lines = ["## Tech Debt", ""]
        for item in model.tech_debt:
            lines.append(f"- {item}")
        lines.append("")
        return "\n".join(lines)

    def _format_build_commands_section(self, model: ProjectModel) -> str:
        """Build a commands section using actual project commands.

        Uses extracted build commands when available, falls back
        to language-specific defaults.

        Args:
            model: The project model.

        Returns:
            Markdown-formatted build commands section.
        """
        if not model.build_commands:
            return ""
        lines = ["```bash"]
        for cmd in model.build_commands:
            lines.append(cmd)
        lines.append("```")
        lines.append("")
        return "\n".join(lines)
