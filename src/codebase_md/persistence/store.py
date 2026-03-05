"""Store for reading and writing .codebase/ directory state.

Manages the .codebase/ directory structure including config.yaml,
project.json (scan output), and decisions.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from codebase_md.model.project import ProjectModel

CODEBASE_DIR = ".codebase"
CONFIG_FILE = "config.yaml"
PROJECT_FILE = "project.json"
DECISIONS_FILE = "decisions.json"

DEFAULT_CONFIG: dict[str, object] = {
    "version": 1,
    "generators": [
        "claude",
        "cursor",
        "agents",
        "codex",
        "windsurf",
        "generic",
    ],
    "scan": {
        "exclude": [
            "node_modules",
            ".venv",
            "dist",
            "build",
            "__pycache__",
            ".git",
        ],
        "depth": "full",
        "registries": True,
    },
    "hooks": {
        "post_commit": True,
        "pre_push": False,
    },
    "depshift": {
        "auto_check": True,
        "severity_threshold": "medium",
    },
}


class StoreError(Exception):
    """Base exception for persistence store operations."""


class ConfigNotFoundError(StoreError):
    """Raised when .codebase/config.yaml is not found."""


class ProjectNotFoundError(StoreError):
    """Raised when .codebase/project.json is not found."""


class Store:
    """Manages the .codebase/ directory for a project.

    Provides read/write access to config, project state, and decisions.

    Args:
        root_path: Path to the project root directory.
    """

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path.resolve()
        self._codebase_dir = self._root_path / CODEBASE_DIR

    @property
    def codebase_dir(self) -> Path:
        """Return the absolute path to the .codebase/ directory."""
        return self._codebase_dir

    @property
    def is_initialized(self) -> bool:
        """Check if .codebase/ directory exists with a config file."""
        return (self._codebase_dir / CONFIG_FILE).is_file()

    def init(self) -> Path:
        """Initialize the .codebase/ directory with default config.

        Creates the directory and writes a default config.yaml.

        Returns:
            Path to the created .codebase/ directory.

        Raises:
            StoreError: If the directory cannot be created.
        """
        try:
            self._codebase_dir.mkdir(parents=True, exist_ok=True)
            self._write_config(DEFAULT_CONFIG)

            # Create a .gitignore inside .codebase/ to ignore sessions
            gitignore_path = self._codebase_dir / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text("sessions/\n", encoding="utf-8")

            return self._codebase_dir
        except OSError as e:
            raise StoreError(f"Failed to initialize .codebase/ in {self._root_path}: {e}") from e

    def read_config(self) -> dict[str, object]:
        """Read the .codebase/config.yaml file.

        Returns:
            Parsed config dictionary.

        Raises:
            ConfigNotFoundError: If config.yaml does not exist.
            StoreError: If the file cannot be read or parsed.
        """
        config_path = self._codebase_dir / CONFIG_FILE
        if not config_path.is_file():
            raise ConfigNotFoundError(
                f"Config not found at {config_path}. Run 'codebase init' first."
            )
        try:
            content = config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise StoreError(f"Invalid config format in {config_path}: expected a mapping")
            return data
        except yaml.YAMLError as e:
            raise StoreError(f"Failed to parse {config_path}: {e}") from e

    def write_project(self, model: ProjectModel) -> Path:
        """Write the ProjectModel to .codebase/project.json.

        Args:
            model: The scanned project model to persist.

        Returns:
            Path to the written project.json file.

        Raises:
            StoreError: If the file cannot be written.
        """
        self._ensure_initialized()
        project_path = self._codebase_dir / PROJECT_FILE
        try:
            data = model.model_dump(mode="json")
            project_path.write_text(
                json.dumps(data, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            return project_path
        except (OSError, TypeError) as e:
            raise StoreError(f"Failed to write project state to {project_path}: {e}") from e

    def read_project(self) -> ProjectModel:
        """Read the ProjectModel from .codebase/project.json.

        Returns:
            The deserialized ProjectModel.

        Raises:
            ProjectNotFoundError: If project.json does not exist.
            StoreError: If the file cannot be read or parsed.
        """
        project_path = self._codebase_dir / PROJECT_FILE
        if not project_path.is_file():
            raise ProjectNotFoundError(
                f"Project state not found at {project_path}. Run 'codebase scan' first."
            )
        try:
            content = project_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return ProjectModel.model_validate(data)
        except json.JSONDecodeError as e:
            raise StoreError(f"Invalid JSON in {project_path}: {e}") from e
        except Exception as e:
            raise StoreError(f"Failed to load project from {project_path}: {e}") from e

    def _write_config(self, config: dict[str, object]) -> None:
        """Write config dictionary to .codebase/config.yaml.

        Args:
            config: Configuration dictionary to write.

        Raises:
            StoreError: If the file cannot be written.
        """
        config_path = self._codebase_dir / CONFIG_FILE
        try:
            config_path.write_text(
                yaml.dump(config, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        except OSError as e:
            raise StoreError(f"Failed to write config to {config_path}: {e}") from e

    def _ensure_initialized(self) -> None:
        """Ensure .codebase/ is initialized before operations.

        Raises:
            StoreError: If .codebase/ has not been initialized.
        """
        if not self.is_initialized:
            raise StoreError(
                f".codebase/ not initialized in {self._root_path}. Run 'codebase init' first."
            )
