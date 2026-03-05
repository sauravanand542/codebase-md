# codex.md — codebase-md

## Overview

`codebase-md` built with python (cli_tool architecture) with 3 module(s) and 14 dependencies.

## Setup

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## Project Structure

- **Architecture:** cli_tool
- **Entry points:** `src/codebase_md/cli.py`

**Modules:**
- `agents`
- `docs`
- `src`

## Conventions

- **Naming:** mixed
- **File Organization:** flat
- **Import Style:** mixed

## Dependencies

typer (>=0.9.0), rich (>=13.0.0), pydantic (>=2.0.0), pyyaml (>=6.0), httpx (>=0.25.0), pytest (>=7.0.0), pytest-cov (>=4.0.0), ruff (>=0.4.0), mypy (>=1.8.0), types-PyYAML (>=6.0), tree-sitter (>=0.21.0), tree-sitter-python (>=0.21.0), tree-sitter-javascript (>=0.21.0), tree-sitter-typescript (>=0.21.0)
