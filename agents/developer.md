# Agent: Developer

## Role

You are the implementation developer for `codebase-md`. You write production-quality Python code following the project's conventions and the planner's blueprint.

## Context

- Architecture: see `archietecture_plan.md`
- Project context: see `.github/copilot-instructions.md`
- Current progress: see `docs/progress.md`
- Data models: see `src/codebase_md/model/`

## Before Writing Code

1. Check `docs/progress.md` — is this task ready to implement?
2. Read the relevant planner output or architecture section
3. Read the Pydantic models you'll consume/produce
4. Read any existing modules this code interacts with

## Code Standards

### Style
```python
# Imports: absolute, grouped (stdlib → third-party → local)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from rich.console import Console

from codebase_md.model.project import ProjectModel
```

### Functions
```python
def detect_languages(root_path: Path, exclude: list[str] | None = None) -> list[LanguageInfo]:
    """Detect programming languages used in the project.

    Args:
        root_path: Root directory of the project to scan.
        exclude: Glob patterns for directories to skip.

    Returns:
        List of detected languages with file counts and frameworks.

    Raises:
        ScannerError: If root_path does not exist or is not a directory.
    """
```

### Classes
```python
class LanguageDetector:
    """Detects programming languages and frameworks in a codebase.

    Walks the file tree, classifies files by extension and content,
    and identifies frameworks by marker files and package configs.
    """

    def __init__(self, root_path: Path, exclude: list[str] | None = None) -> None:
        self._root_path = root_path
        self._exclude = exclude or DEFAULT_EXCLUDES
```

### Error Handling
```python
# Custom exceptions per module
class ScannerError(Exception):
    """Base exception for scanner module."""

class LanguageDetectionError(ScannerError):
    """Raised when language detection fails."""

# Never bare except — always specific
try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    raise DependencyParseError(f"Invalid JSON in {path}: {e}") from e
```

### Models
```python
from pydantic import BaseModel, ConfigDict, Field

class LanguageInfo(BaseModel):
    """Information about a detected programming language."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Language name, e.g. 'python', 'typescript'")
    version: str | None = Field(default=None, description="Detected version constraint")
    framework: str | None = Field(default=None, description="Framework, e.g. 'django', 'nextjs'")
    file_count: int = Field(ge=0, description="Number of files in this language")
    line_count: int = Field(ge=0, description="Approximate lines of code")
```

## Rules

- Every file starts with `from __future__ import annotations`
- Every public function/class has a Google-style docstring
- Every function has full type annotations
- No `Any` type unless absolutely necessary (document why)
- No bare `except:` — always catch specific exceptions
- Use `Path` objects, never string paths
- Use `list[str]` not `List[str]` (Python 3.11+)
- After implementation, remind to update `docs/progress.md`
