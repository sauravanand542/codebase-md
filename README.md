# codebase-md

**The universal project brain that works with every AI coding tool.**

[![CI](https://github.com/sauravanand542/codebase-md/actions/workflows/ci.yml/badge.svg)](https://github.com/sauravanand542/codebase-md/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-173%20passed-brightgreen.svg)]()

One command scans your codebase and generates context files for **Claude Code, Cursor, Codex, Windsurf**, and more — auto-detected conventions, dependency health, architecture maps, and smart context routing. Stays fresh via git hooks.

---

## Why?

Every AI coding tool needs project context to work well. But each tool has its own format:
- Claude Code wants `CLAUDE.md`
- Cursor wants `.cursorrules`
- Codex wants `codex.md`
- Windsurf wants `.windsurfrules`

Writing and maintaining these manually is tedious. **codebase-md** scans your project once and generates all of them from a single source of truth.

## Features

- **Universal output** — generates 6 formats from one scan (CLAUDE.md, .cursorrules, AGENTS.md, codex.md, .windsurfrules, PROJECT_CONTEXT.md)
- **Auto-detected conventions** — naming style, import patterns, file organization, design patterns (powered by tree-sitter AST)
- **Dependency intelligence** — health scores, version diffs, breaking change detection, migration plans with code impact
- **Architecture mapping** — detects monolith/monorepo/microservice/library/CLI patterns, entry points, modules
- **Smart context routing** — query-based context retrieval with TF-IDF relevance scoring
- **Git integration** — hooks for auto-regeneration on commit, contributor analysis, file hotspots
- **Multi-language** — Python, JavaScript, TypeScript (50+ file extensions recognized)

---

## Installation

### From GitHub (recommended for now)

```bash
pip install git+https://github.com/sauravanand542/codebase-md.git
```

### With AST support (recommended)

```bash
pip install "codebase-md[ast] @ git+https://github.com/sauravanand542/codebase-md.git"
```

### For development

```bash
git clone https://github.com/sauravanand542/codebase-md.git
cd codebase-md
pip install -e ".[dev,ast]"
```

---

## Quick Start

```bash
# Initialize config in your project
cd your-project/
codebase init

# Scan your codebase (builds internal project model)
codebase scan .

# Generate context files for all AI tools
codebase generate .
```

That's it. You now have `CLAUDE.md`, `.cursorrules`, `AGENTS.md`, `codex.md`, `.windsurfrules`, and `PROJECT_CONTEXT.md` in your project root.

---

## Commands

### `codebase scan`

Scans your project and builds a complete model: languages, architecture, dependencies, conventions, modules, git history.

```bash
codebase scan .                    # Scan current directory
codebase scan /path/to/project     # Scan a specific project
```

### `codebase generate`

Generates context files from the last scan.

```bash
codebase generate .                # Generate all formats
codebase generate . --format claude  # Generate only CLAUDE.md
```

### `codebase deps`

Dependency health dashboard — checks versions against registries, computes health scores.

```bash
codebase deps .                    # Health dashboard (queries PyPI/npm)
codebase deps . --offline          # Offline mode (no network)
codebase deps . --upgrade typer    # Migration plan for a specific package
```

### `codebase context`

Query relevant project context with smart ranking.

```bash
codebase context "architecture"              # Find architecture info
codebase context "dependencies" --max 3      # Top 3 relevant chunks
codebase context "how to test" --compact     # Content-only output
```

### `codebase hooks`

Install git hooks for automatic regeneration.

```bash
codebase hooks install .           # Install post-commit hooks
codebase hooks status .            # Show installed hooks
codebase hooks remove .            # Remove hooks
```

### `codebase init`

Initialize `.codebase/` configuration directory.

```bash
codebase init                      # Creates .codebase/config.yaml
```

---

## Output Formats

| Format | File | AI Tool | Description |
|---|---|---|---|
| `claude` | `CLAUDE.md` | Claude Code | Structured markdown with project summary, architecture, conventions |
| `cursor` | `.cursorrules` | Cursor | Coding rules, language-specific guidance, tech stack |
| `agents` | `AGENTS.md` | Multi-agent | Compact entry points, commands, architecture flow |
| `codex` | `codex.md` | Codex CLI | Overview, setup, project structure, conventions |
| `windsurf` | `.windsurfrules` | Windsurf | Rules-based format with architecture and file map |
| `generic` | `PROJECT_CONTEXT.md` | Any tool | Complete markdown with all sections + metadata |

---

## What Gets Detected

### Languages & Frameworks
50+ file extensions recognized. Framework detection for Python (Django, FastAPI, Flask), JavaScript/TypeScript (React, Next.js, Express, Vue).

### Architecture Patterns
Monolith, monorepo, microservice, library, CLI tool — detected from folder structure, entry points, and package layout.

### Conventions
- **Naming**: snake_case, camelCase, PascalCase, kebab-case
- **Imports**: absolute, relative, mixed
- **File organization**: modular, layer-based, feature-based, flat
- **Design patterns**: model, view, controller, service, repository, etc.

### Dependencies
Parses `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`. Health scoring via live registry queries (PyPI, npm).

---

## Project Structure

```
src/codebase_md/
├── cli.py                  # Typer CLI — all commands
├── model/                  # Pydantic v2 data models (frozen, validated)
├── scanner/                # Codebase analysis engine
│   ├── engine.py           # Orchestrates all scanners
│   ├── language_detector.py
│   ├── structure_analyzer.py
│   ├── dependency_parser.py
│   ├── convention_inferrer.py  # tree-sitter powered
│   ├── ast_analyzer.py        # tree-sitter AST
│   └── git_analyzer.py
├── generators/             # Output format generators (plugin-style)
├── depshift/               # Dependency intelligence engine
│   ├── analyzer.py         # Health scoring
│   ├── version_differ.py   # Breaking change detection
│   ├── usage_mapper.py     # Import → source location mapping
│   └── registries/         # PyPI + npm clients
├── context/                # Smart context routing
│   ├── chunker.py          # 12 topic-based chunks
│   ├── ranker.py           # 6-signal TF-IDF scoring
│   └── router.py           # Query pipeline
├── persistence/            # .codebase/ state management
└── integrations/           # Git hooks, GitHub Actions
```

---

## Configuration

After `codebase init`, edit `.codebase/config.yaml`:

```yaml
version: 1
generators:
  - claude
  - cursor
  - agents
  - codex
  - windsurf
  - generic
scan:
  exclude:
    - node_modules
    - .venv
    - dist
    - build
hooks:
  post_commit: true
  pre_push: false
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions, and PR guidelines.

## License

[MIT](LICENSE)
