# Architecture Plan: `codebase.md`

**The universal project brain that works with every AI coding tool.**

One command scans your codebase and generates context files for Claude Code, Cursor, Codex, Windsurf, and more — auto-detected conventions, dependency health, architecture maps, and smart context routing. Stays fresh via git hooks.

---

## High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                        codebase.md CLI                              │
│                                                                     │
│  codebase scan    codebase generate    codebase deps    codebase watch│
└──────────┬──────────────┬─────────────────┬──────────────┬──────────┘
           │              │                 │              │
           ▼              ▼                 ▼              ▼
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────┐
│   Scanner    │  │  Generators   │  │  DepShift    │  │  Watcher  │
│   Engine     │  │  (Outputs)    │  │  Engine      │  │  (Hooks)  │
└──────┬───────┘  └───────┬───────┘  └──────┬───────┘  └──────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Project Model (Internal)                        │
│                                                                     │
│  Architecture │ Dependencies │ Conventions │ Decisions │ Contexts   │
│               │              │             │           │            │
│  .codebase/project.json  (persisted state)                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Package Structure

```
codebase-md/
├── pyproject.toml                    # Project config (uv/pip compatible)
├── README.md
├── LICENSE                           # MIT
├── CONTRIBUTING.md
├── .github/
│   └── workflows/
│       └── ci.yml                    # Tests + lint on PR
│
├── src/
│   └── codebase_md/
│       ├── __init__.py               # Version, entry point
│       ├── cli.py                    # Typer CLI app (main entry)
│       │
│       ├── scanner/                  # Phase 1: Analyze the codebase
│       │   ├── __init__.py
│       │   ├── engine.py             # Orchestrates all scanners
│       │   ├── language_detector.py  # Detect languages/frameworks used
│       │   ├── structure_analyzer.py # Folder structure → architecture type
│       │   ├── dependency_parser.py  # package.json, requirements.txt, etc.
│       │   ├── convention_inferrer.py # Naming, patterns, file org
│       │   ├── ast_analyzer.py       # tree-sitter based code analysis
│       │   └── git_analyzer.py       # Git history, contributors, activity
│       │
│       ├── model/                    # Internal representation
│       │   ├── __init__.py
│       │   ├── project.py            # Root project model
│       │   ├── module.py             # Service/package/module
│       │   ├── dependency.py         # Dep with version, usage, health
│       │   ├── convention.py         # Detected convention
│       │   ├── architecture.py       # Architecture pattern
│       │   └── decision.py           # Architectural decision record
│       │
│       ├── depshift/                 # Dependency intelligence
│       │   ├── __init__.py
│       │   ├── analyzer.py           # Core dep analysis
│       │   ├── version_differ.py     # Compare versions, find breaking changes
│       │   ├── usage_mapper.py       # Map dep APIs → your code locations
│       │   ├── changelog_parser.py   # Parse changelogs for breaking changes
│       │   └── registries/
│       │       ├── __init__.py
│       │       ├── npm.py            # npm registry client
│       │       └── pypi.py           # PyPI registry client
│       │
│       ├── generators/              # Phase 2: Output to AI tool formats
│       │   ├── __init__.py
│       │   ├── base.py              # Abstract generator interface
│       │   ├── claude_md.py         # → CLAUDE.md
│       │   ├── cursorrules.py       # → .cursorrules
│       │   ├── agents_md.py         # → AGENTS.md
│       │   ├── codex_md.py          # → codex.md
│       │   ├── windsurf.py          # → .windsurfrules
│       │   └── generic_md.py        # → generic markdown
│       │
│       ├── context/                 # Smart context routing
│       │   ├── __init__.py
│       │   ├── chunker.py           # Split knowledge into topic chunks
│       │   ├── router.py            # Route relevant context to queries
│       │   └── ranker.py            # Relevance scoring
│       │
│       ├── persistence/             # State management
│       │   ├── __init__.py
│       │   ├── store.py             # Read/write .codebase/ directory
│       │   └── decisions.py         # Decision log management
│       │
│       └── integrations/            # Hooks & CI
│           ├── __init__.py
│           ├── git_hooks.py         # Install/manage git hooks
│           └── github_action.py     # GitHub Action generator
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/                    # Sample repos for testing
│   │   ├── nextjs_app/
│   │   ├── fastapi_app/
│   │   ├── monorepo/
│   │   └── django_app/
│   ├── test_scanner/
│   ├── test_model/
│   ├── test_depshift/
│   ├── test_generators/
│   └── test_context/
│
└── docs/
    ├── architecture.md
    ├── contributing.md
    └── generators.md
```

---

## Core Data Model

The central `ProjectModel` is what everything reads from and writes to:

```
ProjectModel
├── name: str
├── root_path: Path
├── languages: list[LanguageInfo]          # {name, version, framework, file_count, line_count}
├── architecture: ArchitectureInfo          # {type: monolith|monorepo|microservice, entry_points, services}
├── modules: list[ModuleInfo]               # Logical groupings (backend, frontend, shared, etc.)
│   └── files: list[FileInfo]              # {path, language, exports, imports, purpose}
├── dependencies: list[DependencyInfo]      # {name, version, latest, health_score, usage_locations, breaking_changes}
├── conventions: ConventionSet              # {naming, file_org, import_style, test_pattern, patterns_used}
├── tech_debt: list[TechDebtItem]           # {location, type, severity, description}
├── security: SecurityPosture               # {auth_method, env_var_handling, known_issues}
├── testing: TestingInfo                    # {framework, coverage_pct, pattern, test_locations}
├── decisions: list[DecisionRecord]         # {date, title, context, choice, alternatives, consequences}
├── api_surface: list[APIEndpoint]          # {method, path, handler, auth_required}
└── metadata: ScanMetadata                  # {scanned_at, version, git_sha, scan_duration}
```

---

## CLI Commands

| Command | Description |
|---|---|
| `codebase scan` | Full scan of the project, builds `ProjectModel`, saves to `.codebase/` |
| `codebase generate` | Generate all configured output files (CLAUDE.md, .cursorrules, etc.) |
| `codebase generate --format claude` | Generate only a specific format |
| `codebase deps` | Show dependency health dashboard |
| `codebase deps upgrade react` | Show migration plan for a specific dependency |
| `codebase decisions add` | Interactive prompt to record an architectural decision |
| `codebase decisions list` | Show all recorded decisions |
| `codebase init` | Initialize `.codebase/` config in a project |
| `codebase watch` | Watch for file changes and regenerate |
| `codebase hooks install` | Install git hooks for auto-regeneration |
| `codebase diff` | Show what changed since last scan |

---

## Scanner Pipeline (How `codebase scan` Works)

```
Step 1: Language Detection
    → Walk file tree, classify by extension + content
    → Detect frameworks (Next.js, Django, FastAPI, Express, etc.)
    → Output: list[LanguageInfo]

Step 2: Structure Analysis
    → Analyze folder hierarchy
    → Detect architecture pattern (monolith, monorepo, microservice)
    → Identify entry points, services, shared code
    → Output: ArchitectureInfo, list[ModuleInfo]

Step 3: Dependency Parsing
    → Read package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml
    → Query registries for latest versions
    → Calculate health scores (staleness, CVEs, maintenance status)
    → Output: list[DependencyInfo]

Step 4: Convention Inference (AST-powered)
    → Parse sample files with tree-sitter
    → Detect naming conventions (camelCase vs snake_case)
    → Detect import patterns (absolute vs relative, barrel files)
    → Detect design patterns (repository, service, controller, etc.)
    → Detect test conventions (where tests live, naming, frameworks)
    → Output: ConventionSet

Step 5: API Surface Detection
    → Find route definitions (Express, FastAPI, Django URLs, etc.)
    → Map endpoints → handlers
    → Detect auth middleware
    → Output: list[APIEndpoint]

Step 6: Git Analysis
    → Most active files (change frequency)
    → Contributors per module
    → Recent activity areas
    → Output: enriches ModuleInfo

Step 7: Assemble & Persist
    → Build complete ProjectModel
    → Save to .codebase/project.json
    → Trigger generators
```

---

## Generator Architecture

Each generator implements a `BaseGenerator` interface:

```
BaseGenerator (abstract)
├── format_name: str                    # "claude", "cursor", etc.
├── output_filename: str                # "CLAUDE.md", ".cursorrules", etc.
├── generate(model: ProjectModel) → str # Produce the output content
└── supports_sections: list[str]        # Which sections this format uses
```

Every generator receives the same `ProjectModel` and transforms it into the right format. The key difference between formats:

- **CLAUDE.md**: Markdown, structured with headers, supports `<context>` blocks
- **.cursorrules**: Markdown with YAML frontmatter, uses `globs` and `alwaysApply`
- **AGENTS.md**: Markdown, cross-tool universal format
- **codex.md**: Markdown, simpler structure for Codex CLI
- **.windsurfrules**: Similar to cursorrules with Windsurf-specific fields
- **Generic**: Clean markdown suitable for any tool's system prompt

---

## DepShift Integration

The dependency intelligence engine is a first-class module, not an afterthought:

```
codebase deps

┌─────────────────────────────────────────────────────────┐
│  Dependency Health Dashboard                             │
├─────────────┬─────────┬────────┬────────┬───────────────┤
│ Package     │ Current │ Latest │ Health │ Action        │
├─────────────┼─────────┼────────┼────────┼───────────────┤
│ react       │ 17.0.2  │ 19.1.0 │ ▓▓░░░  │ 5 breaking   │
│ express     │ 4.18.2  │ 5.1.0  │ ▓▓▓░░  │ 3 breaking   │
│ lodash      │ 4.17.21 │ 4.17.21│ ▓▓▓▓▓  │ up to date   │
│ jsonwebtoken│ 8.5.1   │ 10.0.1 │ ▓░░░░  │ 7 breaking   │
└─────────────┴─────────┴────────┴────────┴───────────────┘

codebase deps upgrade react

→ React 17.0.2 → 19.1.0 Migration Plan
  
  YOUR code impact:
  ├── src/index.tsx:5      → ReactDOM.render() — REMOVED in React 18
  │   Fix: Use createRoot() from 'react-dom/client'
  ├── src/App.tsx:12       → componentWillMount — REMOVED in React 17
  │   Fix: Use useEffect() or constructor
  └── src/utils/legacy.tsx → React.createClass — REMOVED in React 16
      Fix: Use class or function components
  
  Effort estimate: ~4 hours
  Risk: Medium (3 breaking changes across 3 files)
```

---

## `.codebase/` Directory

```
.codebase/
├── config.yaml              # User preferences (which generators, scan depth, etc.)
├── project.json             # Full ProjectModel (auto-generated by scan)
├── decisions.json           # Architectural decision records
├── sessions/                # Session memory for AI tools
│   └── 2026-03-04.json     # What was worked on, decisions made
└── .gitignore               # Ignore sessions (optional)
```

**`config.yaml` example:**

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
  depth: full           # full | shallow (no AST)
  registries: true      # query npm/pypi for dep health
hooks:
  post_commit: true     # auto-regenerate on commit
  pre_push: false
depshift:
  auto_check: true      # include dep health in scan
  severity_threshold: medium
```

---

## Tech Stack

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Builder's strength, rich ecosystem |
| CLI Framework | `typer` + `rich` | Beautiful CLI with minimal code |
| AST Parsing | `tree-sitter` (`py-tree-sitter`) | Multi-language, fast (C-based), supports JS/TS/Python/Go/Rust |
| Package Manager | `uv` (primary), `pip` compatible | Modern, fast, what devs are adopting |
| Config Parsing | `pyyaml` + `tomli` | For reading project configs |
| HTTP Client | `httpx` | Async, modern, for registry queries |
| Testing | `pytest` + `pytest-cov` | Standard |
| Linting | `ruff` | Fast, all-in-one |
| Type Checking | `mypy` | Strict typing for reliability |
| Build | `hatchling` | Modern Python packaging |
| Distribution | `pipx install codebase-md` or `uv tool install codebase-md` | One-command install |

---

## Implementation Phases (Build Order)

### Phase 1 — Foundation (Week 1)

1. Set up repo structure, `pyproject.toml`, CI, linting
2. Build `cli.py` with Typer — stub all commands
3. Build the `model/` — all data classes with Pydantic
4. Build `persistence/store.py` — read/write `.codebase/`

### Phase 2 — Scanner (Week 2)

5. `language_detector.py` — file extension + content detection, framework detection
6. `structure_analyzer.py` — folder hierarchy → architecture type
7. `dependency_parser.py` — parse package.json, requirements.txt, pyproject.toml

### Phase 3 — Generators (Week 3)

8. `base.py` — generator interface
9. `claude_md.py` — CLAUDE.md output
10. `cursorrules.py` — .cursorrules output
11. `agents_md.py`, `codex_md.py`, `windsurf.py`, `generic_md.py`

### Phase 4 — Intelligence (Week 4)

12. `convention_inferrer.py` — tree-sitter based convention detection
13. `ast_analyzer.py` — deeper code analysis
14. `git_analyzer.py` — git history analysis

### Phase 5 — DepShift (Week 5)

15. `depshift/analyzer.py` — core dependency analysis
16. `depshift/usage_mapper.py` — map deps to your code
17. `depshift/registries/` — npm + pypi clients
18. `depshift/version_differ.py` — breaking change detection

### Phase 6 — Context Routing (Week 6)

19. `context/chunker.py` — split knowledge into topic chunks
20. `context/ranker.py` — relevance scoring with TF-IDF
21. `context/router.py` — route relevant context to queries

### Phase 7 — Integrations & Polish (Week 7)

22. `integrations/git_hooks.py` — auto-regeneration hooks
23. `integrations/github_action.py` — generate GH Action config
24. tests/ — comprehensive test suite
25. README, docs, CONTRIBUTING guidelines
26. `.github/workflows/publish.yml` — PyPI trusted publisher (ready, not triggered)

### Phase 8 — Hardening & PyPI (Broken into Sub-Phases)

**8A — `decisions` CLI** — Wire decisions add/list/remove with DecisionLog + Rich ✅
**8B — `diff` CLI** — New `scanner/differ.py` + `DiffResult` model, compare current vs last scan ✅
**8C — `watch` CLI** — File watcher, debounced re-scan + regenerate ✅
**8D — Generator Enrichment** — Enrich all 6 generators with descriptions, build commands, git insights, API surface, key files, module relationships, convention examples, testing/security/tech debt ✅
**8E — Real-World Testing** — Test on 8-10 diverse repos via shallow clones, fix bugs, create regression fixtures (details below)
**8F — Release & PyPI** — Security review, code review, version bump, CHANGELOG, tag + publish

---

## Phase 8E — Real-World Testing Plan

### Approach: Shallow Clones (No Full Repos Needed)

The scanner requires local filesystem access — every sub-scanner walks the file tree, reads manifests, parses source with tree-sitter, and runs `git` commands. **There is no remote scanning mode.**

However, full clones are unnecessary:

| Method | Lang Detection | Structure | Deps | AST | Git Insights | Speed |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|
| `git clone --depth 1` | ✅ | ✅ | ✅ | ✅ | ⚠️ 1 commit | Seconds |
| `git clone --depth 50` | ✅ | ✅ | ✅ | ✅ | ✅ Good | Seconds |
| GitHub ZIP download | ✅ | ✅ | ✅ | ✅ | ❌ No .git | Fastest |
| Full clone | ✅ | ✅ | ✅ | ✅ | ✅ Complete | Slow for large repos |

**Use `git clone --depth 50` into a temp directory.** Fast, full scanner coverage, easy cleanup.

### Test Repos (10 repos, covering all scanner paths)

| # | Repo | Language | Architecture | Validates |
|---|------|----------|-------------|-----------|
| 1 | `codebase-md` itself | Python | cli_tool | Self-test, pyproject.toml, Python AST, snake_case |
| 2 | `fastapi/full-stack-fastapi-template` | Python+TS | monolith | FastAPI detection, API endpoints, mixed-lang, Docker |
| 3 | `create-next-app` output or Next.js example | TypeScript | monolith | package.json, TS AST, Next.js framework, camelCase |
| 4 | `vercel/turborepo` starter | TypeScript | monorepo | Workspace detection, multiple packages, cross-module |
| 5 | `django/django` | Python | library | Large repo perf (4000+ files), complex modules, many contributors |
| 6 | `spf13/cobra-cli` | Go | cli_tool | Go detection, go.mod parsing |
| 7 | `BurntSushi/ripgrep` | Rust | cli_tool | Rust detection, Cargo.toml parsing |
| 8 | `heartcombo/devise` | Ruby | library | Ruby detection, Gemfile parsing |
| 9 | `electron/electron-quick-start` | JS+HTML | monolith | Multiple languages, package.json, mixed conventions |
| 10 | Empty repo (create locally) | — | — | Graceful degradation, no crash on empty |

### Validation Matrix (per repo)

| Check | What to Verify |
|-------|---------------|
| Languages | All detected, primary ranked first, framework found |
| Architecture | Correct type (monolith / monorepo / library / cli_tool) |
| Entry points | Real entry points found (main.py, index.ts, manage.py) |
| Modules | Logical boundaries, not too many / too few |
| Dependencies | All manifest deps parsed, versions correct, dep_type correct |
| Conventions | Naming style, import style, file organization correct |
| AST exports | Real function/class names, sensible purpose inference |
| Git insights | Commits > 0, contributors found, hotspots non-empty |
| Description | Meaningful text from README or manifest |
| Build commands | Real commands (not generic fallbacks) |
| Generator output | All 6 files non-empty, valid markdown, contain real data |

### Test Execution Flow

```
For each test repo:
  1. Shallow clone into temp dir (or use local for self-test)
  2. codebase scan <path> → assert no errors
  3. Assert ProjectModel: languages, architecture, deps, modules are correct
  4. codebase generate <path> → assert all 6 files generated
  5. Assert output contains real project data (not empty/generic)
  6. codebase deps <path> --offline → assert dep table renders
  7. Cleanup temp directory
```

### Expected Bug Categories

| Category | Likely Issue | Fix |
|----------|-------------|-----|
| Large repos | AST analyzer slow on 4000+ files | Verify max_files=200 cap works |
| Monorepos | Too many or too few modules detected | Tune structure_analyzer heuristics |
| Framework detection | May miss Next.js, Django, Rails patterns | Add detection rules |
| Go / Rust AST | tree-sitter grammars not installed | Verify regex fallback fires |
| Ruby Gemfile | Edge cases (groups, git sources) | Fix parser |
| Non-UTF8 files | Binary files crash AST analyzer | Verify UnicodeDecodeError caught |
| Symlinks | Possible infinite loops in file walker | Add symlink detection |
| Permissions | Unreadable files crash scanners | Verify PermissionError caught |

### Regression Fixtures (created after testing)

```
tests/fixtures/
├── python_cli/     # pyproject.toml, src/, tests/ (5 files)
├── nextjs_app/     # package.json, pages/, next.config.js (5 files)
├── fastapi_app/    # main.py, requirements.txt, routes/ (5 files)
├── monorepo/       # packages/a/, packages/b/, root package.json (8 files)
├── go_cli/         # go.mod, main.go, cmd/ (4 files)
├── rust_cli/       # Cargo.toml, src/main.rs (3 files)
├── mixed_lang/     # Python + JS in one repo (6 files)
└── empty_repo/     # Just README.md (1 file)
```

Each fixture is tiny (3-10 files) and runs in normal `pytest` with no network.
Integration tests (real clones) use `@pytest.mark.integration` and run separately.

---

## Verification Strategy

- `pytest` with fixture repos (a Next.js app, a FastAPI app, a Django app, a monorepo) to validate scanner output
- Integration tests: scan fixture → generate → validate output format is valid for each tool
- CLI tests: all commands work with `--help`, error gracefully on missing project
- Manual: run on 5-10 popular open source repos (Next.js, FastAPI, Django) and verify the generated files are useful

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python | Builder's strength, tree-sitter bindings, target audience familiarity |
| AST parsing | tree-sitter over `ast` module | Multi-language support from day 1 (JS, TS, Python, Go, Rust) with one parser |
| Data models | Pydantic | Validation, serialization, type safety — free schema enforcement |
| Generator pattern | Plugin-style abstract base | Each generator is independent, community can add new ones without touching core |
| State location | `.codebase/` directory | Project-local state, git-committable config, session memory stays local |
| Output formats | All 6 in v1 | The "works with every tool" message is the viral hook — shipping with only 2 weakens the pitch |
| Scope v1 languages | JS/TS + Python | Covers ~80% of vibe coders |
