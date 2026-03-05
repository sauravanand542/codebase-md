"""Tests for codebase_md.context.ranker."""

from __future__ import annotations

from codebase_md.context.chunker import ChunkTopic, ContextChunk
from codebase_md.context.ranker import ScoredChunk, rank_chunks


def _make_chunk(
    chunk_id: str,
    topic: ChunkTopic,
    title: str,
    content: str,
    tags: list[str] | None = None,
    priority: float = 0.5,
) -> ContextChunk:
    """Helper to create test chunks."""
    return ContextChunk(
        chunk_id=chunk_id,
        topic=topic,
        title=title,
        content=content,
        tags=tags or [],
        priority=priority,
    )


class TestRankChunks:
    """Tests for rank_chunks function."""

    def test_returns_scored_chunks(self) -> None:
        """Should return ScoredChunk instances."""
        chunks = [
            _make_chunk("arch", ChunkTopic.ARCHITECTURE, "Architecture", "monolith pattern",
                        tags=["architecture", "monolith"]),
        ]
        scored = rank_chunks("architecture", chunks)
        assert len(scored) == 1
        assert isinstance(scored[0], ScoredChunk)
        assert scored[0].score > 0

    def test_ranks_relevant_higher(self) -> None:
        """Should rank matching chunks higher."""
        chunks = [
            _make_chunk("deps", ChunkTopic.DEPENDENCIES, "Dependencies",
                        "react, express, lodash", tags=["dependencies", "npm"]),
            _make_chunk("arch", ChunkTopic.ARCHITECTURE, "Architecture",
                        "monolith pattern", tags=["architecture"]),
        ]
        scored = rank_chunks("dependencies npm", chunks)
        # Dependencies chunk should score higher
        assert scored[0].chunk.chunk_id == "deps"

    def test_tag_matching_boosts_score(self) -> None:
        """Should boost score when query matches tags."""
        chunks = [
            _make_chunk("tagged", ChunkTopic.CONVENTIONS, "Conventions",
                        "snake_case naming", tags=["conventions", "naming", "snake_case"]),
            _make_chunk("untagged", ChunkTopic.OVERVIEW, "Overview",
                        "project overview", tags=["overview"]),
        ]
        scored = rank_chunks("naming conventions", chunks)
        assert scored[0].chunk.chunk_id == "tagged"

    def test_empty_query(self) -> None:
        """Should handle empty query gracefully (raises RankingError)."""
        from codebase_md.context.ranker import RankingError

        chunks = [
            _make_chunk("a", ChunkTopic.OVERVIEW, "Overview", "content", priority=0.9),
        ]
        import pytest

        with pytest.raises(RankingError):
            rank_chunks("", chunks)

    def test_empty_chunks(self) -> None:
        """Should return empty list for empty chunks."""
        scored = rank_chunks("test", [])
        assert scored == []

    def test_sorted_by_score_descending(self) -> None:
        """Should return chunks sorted by score descending."""
        chunks = [
            _make_chunk("low", ChunkTopic.GIT_METADATA, "Git", "metadata",
                        tags=["git"], priority=0.1),
            _make_chunk("high", ChunkTopic.ARCHITECTURE, "Architecture",
                        "architecture type detection", tags=["architecture", "type"],
                        priority=0.9),
        ]
        scored = rank_chunks("architecture type", chunks)
        assert scored[0].score >= scored[-1].score
