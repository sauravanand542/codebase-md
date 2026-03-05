# Contributing to codebase-md

Thanks for your interest in contributing! This guide will help you get set up and understand the project conventions.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Git

### Install

```bash
git clone https://github.com/sauravanand542/codebase-md.git
cd codebase-md
pip install -e ".[dev,ast]"
```

The `dev` extra includes pytest, ruff, mypy. The `ast` extra includes tree-sitter grammars for Python, JavaScript, and TypeScript.

### Verify

```bash
ruff check src/ tests/       # Lint
mypy src/                     # Type check
pytest                        # Run tests (173 tests)
```

All three must pass before submitting a PR.

---

## Code Style

### Enforced by tooling

- **Linter**: `ruff` — PEP 8, import sorting, pyupgrade, bugbear, simplify
- **Type checker**: `mypy` — strict mode, all function signatures must have type hints
- **Formatter**: `ruff format` — double quotes, 100-char line length

### Conventions

- **Naming**: `snake_case` for everything — variables, functions, files, modules
- **Imports**: absolute only (`from codebase_md.model.project import ProjectModel`)
- **Docstrings**: Google-style on all public functions and classes
- **Error handling**: Custom exceptions per module, never bare `except:`
- **Models**: Pydantic v2 `BaseModel` with `model_config = ConfigDict(frozen=True)`
- **Enums**: Use `StrEnum`, not `(str, Enum)`

### Example

```python
"""Module docstring — one line describing purpose."""

from __future__ import annotations

from pathlib import Path

from codebase_md.model.project import ProjectModel


class MyError(Exception):
    """Raised when something specific fails."""


def do_something(path: Path, options: list[str] | None = None) -> str:
    """Do something useful.

    Args:
        path: Root directory to process.
        options: Optional list of options.

    Returns:
        Result string.

    Raises:
        MyError: If path does not exist.
    """
    if not path.exists():
        raise MyError(f"Path does not exist: {path}")
    return "done"
```

---

## Project Structure

```
src/codebase_md/
├── cli.py                  # Typer CLI entry point
├── model/                  # Pydantic data models
├── scanner/                # Codebase analysis (7 modules)
├── generators/             # Output format generators (6 formats)
├── depshift/               # Dependency intelligence engine
├── context/                # Smart context routing
├── persistence/            # .codebase/ state management
└── integrations/           # Git hooks, GitHub Actions
```

Tests mirror the source layout:

```
tests/
├── conftest.py             # Shared fixtures
├── test_cli.py
├── test_model/
├── test_scanner/
├── test_generators/
├── test_depshift/
├── test_context/
├── test_persistence/
└── test_integrations/
```

---

## Testing

### Run tests

```bash
pytest                           # All tests
pytest tests/test_scanner/       # One module
pytest -k "test_detects_cli"     # One test by name
pytest --cov=codebase_md         # With coverage
```

### Writing tests

- One test file per source file
- Use `tmp_path` fixture for filesystem tests
- Use `typer.testing.CliRunner` for CLI tests
- Aim for 80%+ coverage
- Test happy path, edge cases, and error conditions

### Test fixtures

Shared fixtures are in `tests/conftest.py`:
- `sample_project_model` — fully populated `ProjectModel`
- `sample_python_project` — `tmp_path` with pyproject.toml, src/, tests/, .git/
- `initialized_project` — `tmp_path` with `.codebase/config.yaml`

---

## Adding a New Generator

Generators follow a plugin pattern. To add a new format:

1. Create `src/codebase_md/generators/my_format.py`
2. Implement `BaseGenerator`:

```python
from codebase_md.generators.base import BaseGenerator
from codebase_md.model.project import ProjectModel


class MyFormatGenerator(BaseGenerator):
    format_name = "myformat"
    output_filename = ".myformat"

    def generate(self, model: ProjectModel) -> str:
        lines: list[str] = []
        lines.append(f"# {model.name}")
        # ... build your output
        return "\n".join(lines)
```

3. Register it in `src/codebase_md/generators/__init__.py`
4. Add tests in `tests/test_generators/`

---

## Pull Request Process

1. Fork the repo and create a feature branch from `main`
2. Make your changes — keep commits focused
3. Ensure all checks pass: `ruff check src/ tests/ && mypy src/ && pytest`
4. Write/update tests for your changes
5. Open a PR with a clear description of what and why

### PR checklist

- [ ] `ruff check` passes
- [ ] `mypy` passes
- [ ] All tests pass
- [ ] New code has type hints
- [ ] New public functions have docstrings
- [ ] Tests added for new functionality

---

## Architecture Overview

The data flow is:

```
codebase scan → Scanner Engine → ProjectModel → .codebase/project.json
codebase generate → Load ProjectModel → Generators → Output Files
codebase deps → Load ProjectModel → DepShift → Health Dashboard
codebase context → Load ProjectModel → Chunker → Ranker → Ranked Results
```

`ProjectModel` (Pydantic, frozen) is the central data structure that everything reads from and writes to. See `src/codebase_md/model/project.py`.

---

## Questions?

Open an issue on [GitHub](https://github.com/sauravanand542/codebase-md/issues).
