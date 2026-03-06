# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-03-05

### Added
- **9 CLI commands** — `scan`, `init`, `generate`, `deps`, `context`, `hooks`, `decisions`, `diff`, `watch`
- **6 output formats** — CLAUDE.md, .cursorrules, AGENTS.md, codex.md, .windsurfrules, PROJECT_CONTEXT.md
- **Scanner engine** — language detection (50+ extensions), architecture inference (CLI/monolith/monorepo/microservice/library), module discovery, entry point detection, framework detection (Flask, FastAPI, Django, React, Next.js, Vue, Vite, Tailwind, etc.)
- **AST analysis** — tree-sitter based export/import/purpose extraction for Python, JavaScript, TypeScript with regex fallback
- **Convention inference** — naming style, import style, file organization, test patterns, design patterns via tree-sitter + heuristics
- **Git analysis** — commit history, contributors, file hotspots, recent activity, branch detection
- **Dependency parsing** — package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, Gemfile with runtime/dev/optional categorization
- **DepShift** — dependency health analysis with PyPI/npm registry queries, version diffing, usage mapping, changelog parsing, upgrade migration plans
- **Context routing** — intelligent chunking (12 topic types), TF-IDF scoring, relevance ranking for AI-targeted context delivery
- **Integrations** — git hooks (post-commit, pre-push) and GitHub Actions workflow generation
- **Persistence** — `.codebase/` directory for project state, config, and architectural decision records
- **Rich output** — project descriptions, key files with purpose/exports/imports, API surface rendering, git insights, module relationships, convention examples from actual code, build/test/lint commands
- **354 tests** — unit tests, fixture-based regression tests (8 project types), integration tests (10 real-world repos including Django, Express, Jekyll, Turborepo, ripgrep)

### Security
- Shell injection prevention in git hook installation (`shlex.quote`)
- YAML injection prevention in GitHub Action generation (Pydantic validators)
- Bounded HTTP responses for PyPI/npm registry clients (10MB max)
- Build command path traversal prevention
- CLI depth parameter validation (1–20)

### Performance
- Tree-sitter parser caching with `@lru_cache` (eliminates per-file parser recreation)
- O(n) module lookups in differ (pre-built dicts instead of O(n²) linear scans)
- `frozenset` for entry point name lookups
- Glob pattern matching optimization in file exclusion

### Fixed
- Path prefix false positives in module assignment (`mod.path + "/"`)
- Dependency/framework/build-command detection for projects with manifests in subdirectories
- Monorepo detection for generic multi-package layouts
- Docker detection with recursive fallback
- README.markdown support in description extraction
- Link-reference definition line skipping in README parsing
- Symlink loop protection in all file-walking operations
- PermissionError/OSError hardening in file scanning
- Binary file detection and skipping

[0.1.0]: https://github.com/sauravanand542/codebase-md/releases/tag/v0.1.0
