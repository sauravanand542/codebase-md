# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in codebase-md, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email **anandsaurav668@gmail.com** with:

1. Description of the vulnerability
2. Steps to reproduce
3. Impact assessment
4. Suggested fix (if any)

You will receive an acknowledgment within **48 hours** and a detailed response within **7 days**.

## Security Considerations

codebase-md is a **read-only analysis tool** — it scans codebases but does not modify them. However:

- **File system access**: The scanner reads files from the target directory. It respects `.gitignore` patterns and excludes common sensitive directories (`.env`, `node_modules`, `.git`).
- **Network access**: The `codebase deps` command queries PyPI and npm registries for version/health data. Use `--offline` to disable all network access.
- **No credential handling**: codebase-md does not read, store, or transmit credentials, API keys, or secrets.
- **Generated output**: Context files (CLAUDE.md, etc.) may contain project structure information. Review generated files before committing to public repositories.

## Best Practices

- Always review generated context files before sharing them publicly
- Use `--offline` mode if you don't want any network requests
- Keep codebase-md updated to the latest version
