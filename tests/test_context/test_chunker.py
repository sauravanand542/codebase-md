"""Tests for codebase_md.context.chunker."""

from __future__ import annotations

from codebase_md.context.chunker import ChunkTopic, ContextChunk, chunk_project
from codebase_md.model.project import ProjectModel


class TestChunkTopic:
    """Tests for ChunkTopic enum."""

    def test_all_topics_exist(self) -> None:
        """Should have all 12 topic types."""
        topics = list(ChunkTopic)
        assert len(topics) == 12
        assert ChunkTopic.OVERVIEW in topics
        assert ChunkTopic.ARCHITECTURE in topics
        assert ChunkTopic.MODULE in topics
        assert ChunkTopic.DEPENDENCIES in topics
        assert ChunkTopic.CONVENTIONS in topics
        assert ChunkTopic.DECISIONS in topics


class TestContextChunk:
    """Tests for ContextChunk model."""

    def test_creation(self) -> None:
        """Should create a ContextChunk with all fields."""
        chunk = ContextChunk(
            chunk_id="test-chunk",
            topic=ChunkTopic.OVERVIEW,
            title="Test Overview",
            content="Some content",
            tags=["test", "overview"],
            source_field="name",
            priority=0.8,
        )
        assert chunk.chunk_id == "test-chunk"
        assert chunk.topic == ChunkTopic.OVERVIEW
        assert chunk.priority == 0.8

    def test_frozen(self) -> None:
        """Should be immutable."""
        chunk = ContextChunk(
            chunk_id="x",
            topic=ChunkTopic.OVERVIEW,
            title="X",
            content="Y",
        )
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            chunk.title = "changed"  # type: ignore[misc]


class TestChunkProject:
    """Tests for chunk_project function."""

    def test_produces_chunks(self, sample_project_model: ProjectModel) -> None:
        """Should produce multiple chunks from a ProjectModel."""
        chunks = chunk_project(sample_project_model)
        assert len(chunks) > 0
        assert all(isinstance(c, ContextChunk) for c in chunks)

    def test_has_overview_chunk(self, sample_project_model: ProjectModel) -> None:
        """Should include an overview chunk."""
        chunks = chunk_project(sample_project_model)
        topics = [c.topic for c in chunks]
        assert ChunkTopic.OVERVIEW in topics

    def test_has_architecture_chunk(self, sample_project_model: ProjectModel) -> None:
        """Should include an architecture chunk."""
        chunks = chunk_project(sample_project_model)
        topics = [c.topic for c in chunks]
        assert ChunkTopic.ARCHITECTURE in topics

    def test_has_module_chunks(self, sample_project_model: ProjectModel) -> None:
        """Should have one chunk per module."""
        chunks = chunk_project(sample_project_model)
        module_chunks = [c for c in chunks if c.topic == ChunkTopic.MODULE]
        assert len(module_chunks) == len(sample_project_model.modules)

    def test_has_dependency_chunk(self, sample_project_model: ProjectModel) -> None:
        """Should include a dependencies chunk when deps exist."""
        chunks = chunk_project(sample_project_model)
        topics = [c.topic for c in chunks]
        assert ChunkTopic.DEPENDENCIES in topics

    def test_minimal_model(self) -> None:
        """Should handle minimal ProjectModel without crashing."""
        model = ProjectModel(name="minimal", root_path="/tmp/min")
        chunks = chunk_project(model)
        assert len(chunks) >= 1  # At least overview
