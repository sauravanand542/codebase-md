"""Chunker — splits ProjectModel knowledge into topic-based context chunks.

Each chunk represents a focused topic (architecture, a specific module,
dependencies, conventions, etc.) with content, tags for searchability,
and metadata about its source within the ProjectModel.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from codebase_md.model.project import ProjectModel


class ChunkingError(Exception):
    """Raised when chunking a ProjectModel fails."""


class ChunkTopic(StrEnum):
    """Predefined topic categories for context chunks."""

    OVERVIEW = "overview"
    ARCHITECTURE = "architecture"
    MODULE = "module"
    DEPENDENCIES = "dependencies"
    CONVENTIONS = "conventions"
    DECISIONS = "decisions"
    BUILD_RUN = "build_run"
    TECH_STACK = "tech_stack"
    API_SURFACE = "api_surface"
    TESTING = "testing"
    SECURITY = "security"
    GIT_METADATA = "git_metadata"


class ContextChunk(BaseModel):
    """A focused chunk of project context on a single topic.

    Attributes:
        chunk_id: Unique identifier for this chunk (e.g. 'architecture', 'module:backend').
        topic: The broad topic category this chunk belongs to.
        title: Human-readable title for the chunk.
        content: The actual context content as markdown text.
        tags: Keywords for search/matching (lowercase).
        source_field: Which ProjectModel field(s) this chunk was derived from.
        priority: Base priority weight (higher = more important). Range 0.0-1.0.
    """

    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(description="Unique identifier, e.g. 'architecture', 'module:backend'")
    topic: ChunkTopic = Field(description="Broad topic category")
    title: str = Field(description="Human-readable title")
    content: str = Field(description="Markdown-formatted context content")
    tags: list[str] = Field(default_factory=list, description="Lowercase keywords for matching")
    source_field: str = Field(
        default="",
        description="ProjectModel field(s) this chunk derives from",
    )
    priority: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Base priority weight (0.0-1.0)",
    )


def chunk_project(model: ProjectModel) -> list[ContextChunk]:
    """Split a ProjectModel into topic-based context chunks.

    Produces one chunk per logical topic area. Modules get individual
    chunks so queries about a specific module return focused context.

    Args:
        model: The scanned project model to chunk.

    Returns:
        List of ContextChunk instances covering all project knowledge.

    Raises:
        ChunkingError: If chunking fails due to invalid model data.
    """
    try:
        chunks: list[ContextChunk] = []

        chunks.append(_build_overview_chunk(model))
        chunks.append(_build_architecture_chunk(model))

        for mod_chunk in _build_module_chunks(model):
            chunks.append(mod_chunk)

        if model.dependencies:
            chunks.append(_build_dependencies_chunk(model))

        chunks.append(_build_conventions_chunk(model))

        if model.decisions:
            chunks.append(_build_decisions_chunk(model))

        chunks.append(_build_build_run_chunk(model))
        chunks.append(_build_tech_stack_chunk(model))

        if model.api_surface:
            chunks.append(_build_api_surface_chunk(model))

        if model.testing:
            chunks.append(_build_testing_chunk(model))

        if model.security:
            chunks.append(_build_security_chunk(model))

        chunks.append(_build_git_metadata_chunk(model))

        return chunks
    except Exception as e:
        raise ChunkingError(f"Failed to chunk project '{model.name}': {e}") from e


# ---------------------------------------------------------------------------
# Chunk builders — one per topic
# ---------------------------------------------------------------------------


def _build_overview_chunk(model: ProjectModel) -> ContextChunk:
    """Build the project overview chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with project summary.
    """
    lines: list[str] = [
        f"# {model.name}",
        "",
    ]

    if model.languages:
        lines.append(f"**Languages:** {', '.join(model.languages)}")

    arch = model.architecture.architecture_type.value
    if arch != "unknown":
        lines.append(f"**Architecture:** {arch}")

    lines.append(f"**Modules:** {len(model.modules)}")
    lines.append(f"**Dependencies:** {len(model.dependencies)}")

    if model.architecture.entry_points:
        lines.append(f"**Entry points:** {', '.join(model.architecture.entry_points)}")

    tags = [
        "overview",
        "project",
        "summary",
        model.name.lower(),
    ]
    tags.extend(lang.lower() for lang in model.languages)

    return ContextChunk(
        chunk_id="overview",
        topic=ChunkTopic.OVERVIEW,
        title=f"Project Overview — {model.name}",
        content="\n".join(lines),
        tags=tags,
        source_field="name,languages,architecture,modules,dependencies",
        priority=0.9,
    )


def _build_architecture_chunk(model: ProjectModel) -> ContextChunk:
    """Build the architecture chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with architecture details.
    """
    arch = model.architecture
    lines: list[str] = [
        "# Architecture",
        "",
        f"**Type:** {arch.architecture_type.value}",
        "",
    ]

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
        infra.append("frontend")
    if arch.has_backend:
        infra.append("backend")
    if arch.has_database:
        infra.append("database")
    if arch.has_docker:
        infra.append("docker")
    if arch.has_ci:
        infra.append("ci/cd")
    if infra:
        lines.append(f"**Infrastructure:** {', '.join(infra)}")
        lines.append("")

    tags = [
        "architecture",
        "structure",
        "design",
        arch.architecture_type.value,
    ]
    tags.extend(infra)
    if arch.entry_points:
        tags.append("entry")

    return ContextChunk(
        chunk_id="architecture",
        topic=ChunkTopic.ARCHITECTURE,
        title="Architecture",
        content="\n".join(lines),
        tags=tags,
        source_field="architecture",
        priority=0.85,
    )


def _build_module_chunks(model: ProjectModel) -> list[ContextChunk]:
    """Build one chunk per module.

    Args:
        model: The project model.

    Returns:
        List of ContextChunk instances, one per module.
    """
    chunks: list[ContextChunk] = []

    for mod in model.modules:
        lines: list[str] = [
            f"# Module: {mod.name}",
            "",
            f"**Path:** `{mod.path}`",
        ]

        if mod.language:
            lines.append(f"**Language:** {mod.language}")
        if mod.framework:
            lines.append(f"**Framework:** {mod.framework}")
        if mod.purpose:
            lines.append(f"**Purpose:** {mod.purpose}")

        if mod.files:
            lines.append(f"**Files:** {len(mod.files)}")
            lines.append("")

            # List up to 30 files with details
            for fi in mod.files[:30]:
                file_line = f"- `{fi.path}`"
                if fi.purpose:
                    file_line += f" — {fi.purpose}"
                lines.append(file_line)

            if len(mod.files) > 30:
                lines.append(f"- ... and {len(mod.files) - 30} more files")

            # Summarize exports across files
            all_exports: list[str] = []
            for fi in mod.files:
                all_exports.extend(fi.exports)

            if all_exports:
                lines.append("")
                lines.append("**Key exports:**")
                for export in all_exports[:20]:
                    lines.append(f"- `{export}`")
                if len(all_exports) > 20:
                    lines.append(f"- ... and {len(all_exports) - 20} more")

        tags = [
            "module",
            mod.name.lower(),
        ]
        if mod.language:
            tags.append(mod.language.lower())
        if mod.framework:
            tags.append(mod.framework.lower())

        # Extract keywords from file paths
        for fi in mod.files[:10]:
            # Get the filename without extension as a tag
            fname = fi.path.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[0]
            if fname and fname not in ("__init__", "index"):
                tags.append(fname.lower())

        chunks.append(
            ContextChunk(
                chunk_id=f"module:{mod.name}",
                topic=ChunkTopic.MODULE,
                title=f"Module: {mod.name}",
                content="\n".join(lines),
                tags=tags,
                source_field="modules",
                priority=0.7,
            )
        )

    return chunks


def _build_dependencies_chunk(model: ProjectModel) -> ContextChunk:
    """Build the dependencies chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with dependency information.
    """
    lines: list[str] = [
        "# Dependencies",
        "",
        f"**Total:** {len(model.dependencies)}",
        "",
        "| Package | Version | Ecosystem |",
        "|---------|---------|-----------|",
    ]

    for dep in model.dependencies:
        lines.append(f"| {dep.name} | {dep.version} | {dep.ecosystem} |")

    # Group by ecosystem
    ecosystems: dict[str, list[str]] = {}
    for dep in model.dependencies:
        ecosystems.setdefault(dep.ecosystem, []).append(dep.name)

    lines.append("")
    for eco, pkgs in ecosystems.items():
        lines.append(f"**{eco}:** {', '.join(pkgs)}")

    tags = ["dependencies", "packages", "deps", "version"]
    tags.extend(dep.name.lower() for dep in model.dependencies)
    tags.extend(ecosystems.keys())

    return ContextChunk(
        chunk_id="dependencies",
        topic=ChunkTopic.DEPENDENCIES,
        title="Dependencies",
        content="\n".join(lines),
        tags=tags,
        source_field="dependencies",
        priority=0.6,
    )


def _build_conventions_chunk(model: ProjectModel) -> ContextChunk:
    """Build the conventions chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with coding conventions.
    """
    conv = model.conventions
    lines: list[str] = [
        "# Conventions",
        "",
        f"**Naming:** {conv.naming.value}",
        f"**File Organization:** {conv.file_org}",
        f"**Import Style:** {conv.import_style.value}",
    ]

    if conv.test_pattern:
        lines.append(f"**Test Pattern:** `{conv.test_pattern}`")

    if conv.patterns_used:
        lines.append(f"**Design Patterns:** {', '.join(conv.patterns_used)}")

    tags = [
        "conventions",
        "style",
        "naming",
        "patterns",
        conv.naming.value,
        conv.import_style.value,
    ]
    if conv.patterns_used:
        tags.extend(p.lower() for p in conv.patterns_used)

    return ContextChunk(
        chunk_id="conventions",
        topic=ChunkTopic.CONVENTIONS,
        title="Conventions",
        content="\n".join(lines),
        tags=tags,
        source_field="conventions",
        priority=0.75,
    )


def _build_decisions_chunk(model: ProjectModel) -> ContextChunk:
    """Build the decisions chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with architectural decisions.
    """
    lines: list[str] = [
        "# Architectural Decisions",
        "",
        f"**Total:** {len(model.decisions)}",
        "",
    ]

    for dec in model.decisions:
        lines.append(f"## {dec.title}")
        lines.append(f"**Date:** {dec.date}")
        lines.append(f"**Choice:** {dec.choice}")
        if dec.context:
            lines.append(f"**Context:** {dec.context}")
        if dec.alternatives:
            lines.append(f"**Alternatives:** {', '.join(dec.alternatives)}")
        if dec.consequences:
            lines.append(f"**Consequences:** {', '.join(dec.consequences)}")
        lines.append("")

    tags = ["decisions", "adr", "architecture", "choice"]
    for dec in model.decisions:
        # Extract keywords from decision titles
        for word in dec.title.lower().split():
            if len(word) > 3:
                tags.append(word)

    return ContextChunk(
        chunk_id="decisions",
        topic=ChunkTopic.DECISIONS,
        title="Architectural Decisions",
        content="\n".join(lines),
        tags=tags,
        source_field="decisions",
        priority=0.65,
    )


def _build_build_run_chunk(model: ProjectModel) -> ContextChunk:
    """Build the build/run chunk with language-specific commands.

    Args:
        model: The project model.

    Returns:
        ContextChunk with build and run instructions.
    """
    lines: list[str] = [
        "# Build & Run",
        "",
    ]

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
                "",
                "# Type check",
                "mypy src/",
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
                "# Run tests",
                "npm test",
                "",
                "# Development server",
                "npm run dev",
                "",
                "# Build",
                "npm run build",
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
                "",
                "# Lint",
                "golangci-lint run",
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
                "",
                "# Lint",
                "cargo clippy",
                "```",
            ]
        )
    else:
        lines.append("No language-specific build commands detected.")

    tags = [
        "build",
        "run",
        "install",
        "test",
        "commands",
        "setup",
    ]
    tags.extend(langs_lower)

    return ContextChunk(
        chunk_id="build_run",
        topic=ChunkTopic.BUILD_RUN,
        title="Build & Run",
        content="\n".join(lines),
        tags=tags,
        source_field="languages",
        priority=0.7,
    )


def _build_tech_stack_chunk(model: ProjectModel) -> ContextChunk:
    """Build the tech stack chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with technology stack summary.
    """
    lines: list[str] = [
        "# Tech Stack",
        "",
    ]

    if model.languages:
        lines.append(f"**Languages:** {', '.join(model.languages)}")

    # Group dependencies by ecosystem for tech stack view
    ecosystems: dict[str, list[str]] = {}
    for dep in model.dependencies:
        ecosystems.setdefault(dep.ecosystem, []).append(f"{dep.name} {dep.version}")

    for eco, pkgs in ecosystems.items():
        lines.append("")
        lines.append(f"**{eco.upper()} packages:**")
        for pkg in pkgs:
            lines.append(f"- {pkg}")

    # Frameworks from modules
    frameworks: list[str] = []
    for mod in model.modules:
        if mod.framework and mod.framework not in frameworks:
            frameworks.append(mod.framework)
    if frameworks:
        lines.append("")
        lines.append(f"**Frameworks:** {', '.join(frameworks)}")

    tags = [
        "tech",
        "stack",
        "technology",
        "framework",
        "tools",
    ]
    tags.extend(lang.lower() for lang in model.languages)
    tags.extend(dep.name.lower() for dep in model.dependencies)
    if frameworks:
        tags.extend(f.lower() for f in frameworks)

    return ContextChunk(
        chunk_id="tech_stack",
        topic=ChunkTopic.TECH_STACK,
        title="Tech Stack",
        content="\n".join(lines),
        tags=tags,
        source_field="languages,dependencies,modules",
        priority=0.6,
    )


def _build_api_surface_chunk(model: ProjectModel) -> ContextChunk:
    """Build the API surface chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with API endpoint information.
    """
    lines: list[str] = [
        "# API Surface",
        "",
        f"**Endpoints:** {len(model.api_surface)}",
        "",
        "| Method | Path | Handler | Auth |",
        "|--------|------|---------|------|",
    ]

    for ep in model.api_surface:
        auth = "Yes" if ep.auth_required else "No"
        lines.append(f"| {ep.method} | `{ep.path}` | `{ep.handler}` | {auth} |")

    tags = [
        "api",
        "endpoints",
        "routes",
        "http",
        "rest",
    ]
    for ep in model.api_surface:
        tags.append(ep.method.lower())
        # Extract path segments as tags
        for segment in ep.path.strip("/").split("/"):
            if segment and not segment.startswith("{") and not segment.startswith(":"):
                tags.append(segment.lower())

    return ContextChunk(
        chunk_id="api_surface",
        topic=ChunkTopic.API_SURFACE,
        title="API Surface",
        content="\n".join(lines),
        tags=tags,
        source_field="api_surface",
        priority=0.7,
    )


def _build_testing_chunk(model: ProjectModel) -> ContextChunk:
    """Build the testing chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with testing information.
    """
    lines: list[str] = [
        "# Testing",
        "",
    ]

    for item in model.testing:
        lines.append(f"- {item}")

    if model.conventions.test_pattern:
        lines.append(f"\n**Test pattern:** `{model.conventions.test_pattern}`")

    tags = ["testing", "tests", "test", "coverage", "quality"]

    return ContextChunk(
        chunk_id="testing",
        topic=ChunkTopic.TESTING,
        title="Testing",
        content="\n".join(lines),
        tags=tags,
        source_field="testing",
        priority=0.5,
    )


def _build_security_chunk(model: ProjectModel) -> ContextChunk:
    """Build the security chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with security observations.
    """
    lines: list[str] = [
        "# Security",
        "",
    ]

    for item in model.security:
        lines.append(f"- {item}")

    tags = ["security", "auth", "authentication", "vulnerability", "safe"]

    return ContextChunk(
        chunk_id="security",
        topic=ChunkTopic.SECURITY,
        title="Security",
        content="\n".join(lines),
        tags=tags,
        source_field="security",
        priority=0.55,
    )


def _build_git_metadata_chunk(model: ProjectModel) -> ContextChunk:
    """Build the git/metadata chunk.

    Args:
        model: The project model.

    Returns:
        ContextChunk with scan and git metadata.
    """
    lines: list[str] = [
        "# Metadata",
        "",
    ]

    if model.metadata:
        lines.append(f"**Scanned at:** {model.metadata.scanned_at}")
        lines.append(f"**Tool version:** {model.metadata.version}")
        if model.metadata.git_sha:
            lines.append(f"**Git SHA:** `{model.metadata.git_sha}`")
        lines.append(f"**Scan duration:** {model.metadata.scan_duration}s")

    lines.append(f"**Project root:** `{model.root_path}`")

    tags = ["metadata", "git", "scan", "version", "sha"]

    return ContextChunk(
        chunk_id="git_metadata",
        topic=ChunkTopic.GIT_METADATA,
        title="Metadata",
        content="\n".join(lines),
        tags=tags,
        source_field="metadata",
        priority=0.3,
    )
