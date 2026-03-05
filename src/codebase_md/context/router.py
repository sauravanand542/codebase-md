"""Router — route relevant project context to queries.

The main entry point for the context routing pipeline. Given a query
and a ProjectModel, the router chunks the project knowledge, ranks
chunks by relevance, and returns the top-N most useful context chunks
formatted for AI tool consumption.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from codebase_md.context.chunker import ChunkingError, ContextChunk, chunk_project
from codebase_md.context.ranker import RankingError, ScoredChunk, rank_chunks
from codebase_md.model.project import ProjectModel


class RoutingError(Exception):
    """Raised when context routing fails."""


class RoutedContext(BaseModel):
    """Result of routing context for a query.

    Contains the query, the matched chunks with scores, and
    aggregate statistics about the routing result.

    Attributes:
        query: The original query string.
        chunks: Ranked list of relevant ScoredChunks.
        total_chunks: Total number of chunks that were evaluated.
        max_score: Highest relevance score among returned chunks.
        min_score_threshold: The minimum score threshold that was applied.
    """

    model_config = ConfigDict(frozen=True)

    query: str = Field(description="The original query")
    chunks: list[ScoredChunk] = Field(
        default_factory=list,
        description="Ranked relevant chunks with scores",
    )
    total_chunks: int = Field(
        default=0,
        description="Total chunks evaluated",
    )
    max_score: float = Field(
        default=0.0,
        description="Highest relevance score",
    )
    min_score_threshold: float = Field(
        default=0.0,
        description="Minimum score threshold applied",
    )


def route_context(
    query: str,
    model: ProjectModel,
    max_chunks: int = 5,
    min_score: float = 0.1,
) -> RoutedContext:
    """Route the most relevant project context to a query.

    Pipeline:
    1. Chunk the ProjectModel into topic-based context chunks
    2. Rank all chunks by relevance to the query
    3. Filter by minimum score threshold
    4. Return the top-N most relevant chunks

    Args:
        query: The search query or question about the project.
        model: The scanned ProjectModel to extract context from.
        max_chunks: Maximum number of chunks to return (default: 5).
        min_score: Minimum relevance score to include a chunk (default: 0.1).

    Returns:
        RoutedContext with the query, matched chunks, and statistics.

    Raises:
        RoutingError: If the routing pipeline fails.
    """
    if not query.strip():
        raise RoutingError("Query cannot be empty")

    if max_chunks < 1:
        raise RoutingError("max_chunks must be at least 1")

    try:
        # Step 1: Chunk the project
        all_chunks = chunk_project(model)

        # Step 2: Rank by relevance
        scored = rank_chunks(query, all_chunks)

        # Step 3: Filter by minimum score
        filtered = [s for s in scored if s.score >= min_score]

        # Step 4: Take top-N
        top = filtered[:max_chunks]

        max_score = top[0].score if top else 0.0

        return RoutedContext(
            query=query,
            chunks=top,
            total_chunks=len(all_chunks),
            max_score=round(max_score, 4),
            min_score_threshold=min_score,
        )
    except (ChunkingError, RankingError) as e:
        raise RoutingError(f"Context routing failed: {e}") from e
    except Exception as e:
        raise RoutingError(f"Unexpected error during context routing: {e}") from e


def route_context_from_chunks(
    query: str,
    chunks: list[ContextChunk],
    max_chunks: int = 5,
    min_score: float = 0.1,
) -> RoutedContext:
    """Route context using pre-computed chunks.

    Use this when chunks have already been computed (e.g., cached)
    to avoid re-chunking the ProjectModel on every query.

    Args:
        query: The search query or question.
        chunks: Pre-computed list of ContextChunks.
        max_chunks: Maximum number of chunks to return.
        min_score: Minimum relevance score to include.

    Returns:
        RoutedContext with the query and matched chunks.

    Raises:
        RoutingError: If ranking or filtering fails.
    """
    if not query.strip():
        raise RoutingError("Query cannot be empty")

    if max_chunks < 1:
        raise RoutingError("max_chunks must be at least 1")

    try:
        scored = rank_chunks(query, chunks)
        filtered = [s for s in scored if s.score >= min_score]
        top = filtered[:max_chunks]
        max_score = top[0].score if top else 0.0

        return RoutedContext(
            query=query,
            chunks=top,
            total_chunks=len(chunks),
            max_score=round(max_score, 4),
            min_score_threshold=min_score,
        )
    except RankingError as e:
        raise RoutingError(f"Context routing failed: {e}") from e
    except Exception as e:
        raise RoutingError(f"Unexpected error during context routing: {e}") from e


def format_routed_context(result: RoutedContext) -> str:
    """Format routed context as markdown for AI tool consumption.

    Produces a clean markdown document with the most relevant
    context chunks, suitable for inclusion in an AI tool's
    system prompt or context window.

    Args:
        result: The routing result to format.

    Returns:
        Markdown-formatted context string.
    """
    if not result.chunks:
        return f"No relevant context found for query: '{result.query}'"

    lines: list[str] = [
        f"# Context for: {result.query}",
        "",
        f"*{len(result.chunks)} of {result.total_chunks} "
        f"context chunks (score >= {result.min_score_threshold})*",
        "",
        "---",
        "",
    ]

    for i, scored in enumerate(result.chunks, 1):
        chunk = scored.chunk

        # Section header with score
        lines.append(f"## {i}. {chunk.title} (score: {scored.score:.2f})")
        lines.append("")

        # Chunk content
        lines.append(chunk.content)
        lines.append("")

        if scored.matched_terms:
            lines.append(f"*Matched: {', '.join(scored.matched_terms)}*")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def format_routed_context_compact(result: RoutedContext) -> str:
    """Format routed context in a compact form (just content, no metadata).

    Useful when you want to inject context directly into a prompt
    without scores and matching details.

    Args:
        result: The routing result to format.

    Returns:
        Concatenated chunk content as a string.
    """
    if not result.chunks:
        return ""

    sections: list[str] = []
    for scored in result.chunks:
        sections.append(scored.chunk.content)

    return "\n\n---\n\n".join(sections)
