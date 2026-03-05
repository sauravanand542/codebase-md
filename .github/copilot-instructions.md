# Copilot Instructions — codebase-md

## Project Overview

`codebase-md` is a Python CLI tool that scans any codebase and auto-generates context files for AI coding tools (Claude Code, Cursor, Codex, Windsurf, etc.). One command produces CLAUDE.md, .cursorrules, AGENTS.md, codex.md, .windsurfrules — all from one source of truth.

**Tagline:** "The universal project brain that works with every AI coding tool."

## Architecture

See `archietecture_plan.md` for the full architecture. Key points:

- **CLI**: `typer` + `rich` — entry point is `src/codebase_md/cli.py`
- **Scanner Engine**: Orchestrates language detection, structure analysis, dependency parsing, convention inference, AST analysis, git analysis
- **Data Model**: Pydantic v2 models in `src/codebase_md/model/` — `ProjectModel` is the central data structure
- **Generators**: Plugin-style classes in `src/codebase_md/generators/` — each transforms `ProjectModel` → output format
- **DepShift**: Dependency intelligence engine in `src/codebase_md/depshift/`
- **Persistence**: `.codebase/` directory stores config, project state, decisions
- **Integrations**: Git hooks, GitHub Actions

## Tech Stack

- Python 3.11+
- Pydantic v2 for data models
- Typer + Rich for CLI
- tree-sitter (py-tree-sitter) for multi-language AST parsing
- httpx for async HTTP (registry queries)
- pytest + pytest-cov for testing
- ruff for linting
- mypy for type checking
- hatchling for build

## Coding Conventions

- **Style**: PEP 8, enforced by ruff
- **Naming**: snake_case for everything (variables, functions, files, modules)
- **Types**: Strict typing everywhere — all function signatures must have type hints
- **Imports**: absolute imports only (`from codebase_md.model.project import ProjectModel`)
- **Docstrings**: Google-style docstrings on all public functions and classes
- **Error handling**: Custom exceptions in each module, never bare `except:`
- **Testing**: pytest, one test file per source file, aim for 80%+ coverage
- **Models**: Pydantic BaseModel with `model_config = ConfigDict(frozen=True)` for immutable data

## Multi-Agent Workflow

This project uses 8 specialized agent prompts in `agents/`. Each agent has a distinct role and should be invoked in the correct order when building features.

### Agents

| Agent | File | Role |
|---|---|---|
| **Orchestrator** | `agents/orchestrator.md` | Routes work to the correct agent; reads `docs/progress.md` to understand project state; breaks multi-step tasks into ordered operations |
| **Planner** | `agents/planner.md` | Creates detailed implementation plans before any code is written — purpose, I/O, file plan, logic outline, test plan, integration points |
| **Developer** | `agents/developer.md` | Writes production-quality Python code following project conventions and the planner's blueprint |
| **Tester** | `agents/tester.md` | Writes comprehensive pytest tests — happy path, edge cases, error conditions; targets 80%+ coverage |
| **Architect** | `agents/architect.md` | Makes design decisions about module boundaries, data flow, interfaces, and patterns; updates architecture when requirements change |
| **Code Reviewer** | `agents/code-reviewer.md` | Reviews implementations for quality, maintainability, convention adherence, and correctness |
| **Security Reviewer** | `agents/security-reviewer.md` | Audits code for vulnerabilities, unsafe patterns, and security anti-patterns |
| **Doc Writer** | `agents/doc-writer.md` | Writes clear documentation — README, docstrings, API docs, user guides; updates `docs/progress.md` after each phase |

### Standard Build Workflow

1. **Orchestrator** — read `docs/progress.md`, determine what's next
2. **Planner** — break the task into a detailed implementation plan
3. **Developer** — implement the plan (one module at a time)
4. **Tester** — verify with ruff, mypy, and end-to-end tests
5. **Code Reviewer** — review for quality (optional, on complex changes)
6. **Doc Writer** — update `docs/progress.md` after completion

## File Layout Reference

```
src/codebase_md/
├── cli.py                  # Typer app, all CLI commands
├── model/                  # Pydantic data models
├── scanner/                # Codebase analysis engine
├── generators/             # Output format generators
├── depshift/               # Dependency intelligence
├── context/                # Smart context routing
├── persistence/            # .codebase/ state management
└── integrations/           # Git hooks, CI
```

## Development Environment

- **Conda environment**: `codebase-md` (miniforge3, Python 3.11.14)
- **Always activate before running any commands**: `source ~/miniforge3/etc/profile.d/conda.sh && conda activate codebase-md`
- **Install in dev mode**: `pip install -e '.[dev,ast]'`

## Current Build Phase

Check `docs/progress.md` for the current implementation status.
