"""Decision log management for architectural decision records.

Provides read/write access to .codebase/decisions.json,
storing and retrieving DecisionRecord instances.
"""

from __future__ import annotations

import json
from pathlib import Path

from codebase_md.model.decision import DecisionRecord
from codebase_md.persistence.store import CODEBASE_DIR, DECISIONS_FILE, StoreError


class DecisionLogError(StoreError):
    """Raised when decision log operations fail."""


class DecisionLog:
    """Manages the architectural decision log in .codebase/decisions.json.

    Provides methods to add, list, and persist decision records.

    Args:
        root_path: Path to the project root directory.
    """

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path.resolve()
        self._decisions_path = self._root_path / CODEBASE_DIR / DECISIONS_FILE

    def list_decisions(self) -> list[DecisionRecord]:
        """Read and return all decisions from the log.

        Returns:
            List of DecisionRecord instances, ordered by date.

        Raises:
            DecisionLogError: If the file cannot be read or parsed.
        """
        if not self._decisions_path.is_file():
            return []
        try:
            content = self._decisions_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, list):
                raise DecisionLogError(
                    f"Invalid decisions format in {self._decisions_path}: expected a list"
                )
            return [DecisionRecord.model_validate(item) for item in data]
        except json.JSONDecodeError as e:
            raise DecisionLogError(f"Invalid JSON in {self._decisions_path}: {e}") from e

    def add_decision(self, decision: DecisionRecord) -> DecisionRecord:
        """Add a new decision to the log.

        Appends the decision to the existing log and writes it to disk.

        Args:
            decision: The DecisionRecord to add.

        Returns:
            The added DecisionRecord.

        Raises:
            DecisionLogError: If the file cannot be written.
        """
        decisions = self.list_decisions()
        decisions.append(decision)
        self._write_decisions(decisions)
        return decision

    def _write_decisions(self, decisions: list[DecisionRecord]) -> None:
        """Write the full decision list to disk.

        Args:
            decisions: List of DecisionRecord instances to persist.

        Raises:
            DecisionLogError: If the file cannot be written.
        """
        try:
            # Ensure .codebase/ directory exists
            self._decisions_path.parent.mkdir(parents=True, exist_ok=True)
            data = [d.model_dump(mode="json") for d in decisions]
            self._decisions_path.write_text(
                json.dumps(data, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
        except OSError as e:
            raise DecisionLogError(
                f"Failed to write decisions to {self._decisions_path}: {e}"
            ) from e
