# CLAUDE.md — codebase-md

## What Is This Project?

`codebase-md` built with python (cli_tool architecture) with 3 module(s) and 14 dependencies.

## Quick Reference

- **Entry point**: `src/codebase_md/cli.py`
- **Languages**: python
- **Architecture**: cli_tool
- **Modules**: 3
- **Dependencies**: 14
- **Last scanned**: 2026-03-05 05:00:01.136393+00:00

## Architecture

**Type:** cli_tool

**Entry Points:**
- `src/codebase_md/cli.py`

**Infrastructure:** CI/CD

## Build & Run

```bash
# Install in dev mode
pip install -e '.[dev]'

# Run tests
pytest

# Lint
ruff check .
ruff format .
```

## Conventions

- **Naming:** snake_case
- **File Organization:** modular
- **Import Style:** absolute
- **Patterns:** model, module, router, view

## Modules

### agents
- **Path:** `agents`
- **Files:** 8

### docs
- **Path:** `docs`
- **Files:** 1

### src
- **Path:** `src`
- **Language:** python
- **Files:** 40

## Dependencies

| Package | Version | Ecosystem |
|---------|---------|-----------|
| typer | >=0.9.0 | pypi |
| rich | >=13.0.0 | pypi |
| pydantic | >=2.0.0 | pypi |
| pyyaml | >=6.0 | pypi |
| httpx | >=0.25.0 | pypi |
| pytest | >=7.0.0 | pypi |
| pytest-cov | >=4.0.0 | pypi |
| ruff | >=0.4.0 | pypi |
| mypy | >=1.8.0 | pypi |
| types-PyYAML | >=6.0 | pypi |
| tree-sitter | >=0.21.0 | pypi |
| tree-sitter-python | >=0.21.0 | pypi |
| tree-sitter-javascript | >=0.21.0 | pypi |
| tree-sitter-typescript | >=0.21.0 | pypi |
