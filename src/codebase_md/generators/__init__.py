"""Output format generators for codebase-md.

Each generator transforms a ProjectModel into a specific output format
for AI coding tools (CLAUDE.md, .cursorrules, AGENTS.md, codex.md,
.windsurfrules, or generic markdown).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codebase_md.generators.base import BaseGenerator

# Registry mapping format names to generator classes.
# Populated lazily to avoid circular imports.
_REGISTRY: dict[str, type[BaseGenerator]] | None = None


def _build_registry() -> dict[str, type[BaseGenerator]]:
    """Build the generator registry by importing all generator classes.

    Returns:
        Dictionary mapping format names to generator classes.
    """
    from codebase_md.generators.agents_md import AgentsMdGenerator
    from codebase_md.generators.claude_md import ClaudeMdGenerator
    from codebase_md.generators.codex_md import CodexMdGenerator
    from codebase_md.generators.cursorrules import CursorRulesGenerator
    from codebase_md.generators.generic_md import GenericMdGenerator
    from codebase_md.generators.windsurf import WindsurfGenerator

    generators: list[type[BaseGenerator]] = [
        ClaudeMdGenerator,
        CursorRulesGenerator,
        AgentsMdGenerator,
        CodexMdGenerator,
        WindsurfGenerator,
        GenericMdGenerator,
    ]
    return {gen.format_name: gen for gen in generators}


def get_registry() -> dict[str, type[BaseGenerator]]:
    """Get the generator registry, building it on first access.

    Returns:
        Dictionary mapping format names (e.g. 'claude') to generator classes.
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_generator(format_name: str) -> type[BaseGenerator]:
    """Get a generator class by format name.

    Args:
        format_name: Format identifier (e.g. 'claude', 'cursor', 'agents').

    Returns:
        The generator class for the given format.

    Raises:
        KeyError: If the format name is not registered.
    """
    registry = get_registry()
    if format_name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise KeyError(f"Unknown generator format '{format_name}'. Available: {available}")
    return registry[format_name]


AVAILABLE_FORMATS = [
    "claude",
    "cursor",
    "agents",
    "codex",
    "windsurf",
    "generic",
]

__all__ = [
    "AVAILABLE_FORMATS",
    "get_generator",
    "get_registry",
]
