# AGENTS.md — codebase-md

## Project Summary

`codebase-md` built with python (cli_tool architecture) with 3 module(s) and 14 dependencies.

## Entry Points

- `src/codebase_md/cli.py`

## Key Commands

```bash
pip install -e '.[dev]'  # Install
pytest                   # Test
ruff check .             # Lint
mypy src/                # Type check
```

## Conventions

- mixed, mixed imports, flat file organization

## Architecture Flow

**Type:** cli_tool

```
Entry (src/codebase_md/cli.py)
  → Modules: agents, docs, src
```

## Modules

- `agents`
- `docs`
- `src`

## Build Status

See `docs/progress.md` for current implementation state.
