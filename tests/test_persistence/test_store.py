"""Tests for codebase_md.persistence.store."""

from __future__ import annotations

from pathlib import Path

import pytest

from codebase_md.model.project import ProjectModel
from codebase_md.persistence.store import (
    ConfigNotFoundError,
    ProjectNotFoundError,
    Store,
    StoreError,
)


class TestStoreInit:
    """Tests for Store initialization."""

    def test_init_creates_codebase_dir(self, tmp_path: Path) -> None:
        """Should create .codebase/ directory with config.yaml."""
        store = Store(tmp_path)
        result = store.init()
        assert result.is_dir()
        assert (result / "config.yaml").is_file()

    def test_is_initialized_true(self, initialized_project: Path) -> None:
        """Should return True when .codebase/config.yaml exists."""
        store = Store(initialized_project)
        assert store.is_initialized is True

    def test_is_initialized_false(self, tmp_path: Path) -> None:
        """Should return False when .codebase/ doesn't exist."""
        store = Store(tmp_path)
        assert store.is_initialized is False

    def test_init_creates_gitignore(self, tmp_path: Path) -> None:
        """Should create .gitignore inside .codebase/."""
        store = Store(tmp_path)
        codebase_dir = store.init()
        gitignore = codebase_dir / ".gitignore"
        assert gitignore.is_file()
        assert "sessions/" in gitignore.read_text()


class TestStoreConfig:
    """Tests for config read/write."""

    def test_read_config(self, initialized_project: Path) -> None:
        """Should read config.yaml correctly."""
        store = Store(initialized_project)
        config = store.read_config()
        assert config["version"] == 1
        assert "generators" in config

    def test_read_config_not_found(self, tmp_path: Path) -> None:
        """Should raise ConfigNotFoundError when no config.yaml."""
        store = Store(tmp_path)
        with pytest.raises(ConfigNotFoundError):
            store.read_config()


class TestStoreProject:
    """Tests for project.json read/write."""

    def test_write_and_read_project(self, initialized_project: Path) -> None:
        """Should round-trip a ProjectModel through project.json."""
        store = Store(initialized_project)
        model = ProjectModel(name="test", root_path=str(initialized_project))
        store.write_project(model)

        restored = store.read_project()
        assert restored.name == "test"

    def test_read_project_not_found(self, initialized_project: Path) -> None:
        """Should raise ProjectNotFoundError when no project.json."""
        store = Store(initialized_project)
        with pytest.raises(ProjectNotFoundError):
            store.read_project()

    def test_write_project_not_initialized(self, tmp_path: Path) -> None:
        """Should raise StoreError when .codebase/ not initialized."""
        store = Store(tmp_path)
        model = ProjectModel(name="test", root_path=str(tmp_path))
        with pytest.raises(StoreError):
            store.write_project(model)

    def test_project_roundtrip_preserves_data(
        self, initialized_project: Path, sample_project_model: ProjectModel
    ) -> None:
        """Should preserve all ProjectModel fields through serialization."""
        store = Store(initialized_project)
        store.write_project(sample_project_model)
        restored = store.read_project()
        assert restored.name == sample_project_model.name
        assert len(restored.modules) == len(sample_project_model.modules)
        assert len(restored.dependencies) == len(sample_project_model.dependencies)
