# codebase-md

**The universal project brain that works with every AI coding tool.**

One command scans your codebase and generates context files for Claude Code, Cursor, Codex, Windsurf, and more — auto-detected conventions, dependency health, architecture maps, and smart context routing.

## Installation

```bash
pip install codebase-md
```

## Quick Start

```bash
# Initialize config in your project
codebase init

# Scan your codebase
codebase scan

# Generate context files for all AI tools
codebase generate
```

## Output Formats

| Command | Output | For |
|---|---|---|
| `codebase generate --format claude` | `CLAUDE.md` | Claude Code |
| `codebase generate --format cursor` | `.cursorrules` | Cursor |
| `codebase generate --format agents` | `AGENTS.md` | Multi-agent systems |
| `codebase generate --format codex` | `codex.md` | Codex CLI |
| `codebase generate --format windsurf` | `.windsurfrules` | Windsurf |

## License

MIT
