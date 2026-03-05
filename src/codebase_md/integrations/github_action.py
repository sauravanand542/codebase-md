"""GitHub Actions workflow generator for codebase-md.

Generates a GitHub Actions workflow YAML that runs codebase-md
scan and generate on push/PR, optionally committing the changes.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GitHubActionError(Exception):
    """Base exception for GitHub Action generation."""


class ActionConfig(BaseModel):
    """Configuration for the generated GitHub Actions workflow.

    Controls Python version, trigger events, output formats,
    and whether to auto-commit generated files.
    """

    model_config = ConfigDict(frozen=True)

    python_version: str = Field(
        default="3.11",
        description="Python version to use in the workflow.",
    )
    triggers: list[str] = Field(
        default_factory=lambda: ["push", "pull_request"],
        description="GitHub event triggers for the workflow.",
    )
    branches: list[str] = Field(
        default_factory=lambda: ["main"],
        description="Branches to trigger on.",
    )
    auto_commit: bool = Field(
        default=False,
        description="Whether to commit generated files back to the repo.",
    )
    formats: list[str] = Field(
        default_factory=lambda: ["claude", "cursor", "agents", "codex", "windsurf", "generic"],
        description="Output formats to generate.",
    )


def generate_workflow(config: ActionConfig | None = None) -> str:
    """Generate a GitHub Actions workflow YAML string.

    Produces a workflow that installs codebase-md, runs a scan,
    and generates all configured output formats.

    Args:
        config: Workflow configuration. Uses defaults if None.

    Returns:
        YAML string for the workflow file.
    """
    cfg = config or ActionConfig()

    # Build trigger section
    trigger_lines = _build_triggers(cfg)

    # Build steps
    steps = _build_steps(cfg)

    workflow = f"""name: codebase-md

{trigger_lines}

jobs:
  generate-context:
    runs-on: ubuntu-latest

    permissions:
      contents: {'write' if cfg.auto_commit else 'read'}

    steps:
{steps}"""

    return workflow


def write_workflow(root_path: Path, config: ActionConfig | None = None) -> Path:
    """Write the GitHub Actions workflow file to disk.

    Creates or overwrites .github/workflows/codebase-md.yml.

    Args:
        root_path: Project root directory.
        config: Workflow configuration. Uses defaults if None.

    Returns:
        Path to the written workflow file.

    Raises:
        GitHubActionError: If the file cannot be written.
    """
    workflow_dir = root_path / ".github" / "workflows"
    workflow_file = workflow_dir / "codebase-md.yml"

    try:
        workflow_dir.mkdir(parents=True, exist_ok=True)
        content = generate_workflow(config)
        workflow_file.write_text(content, encoding="utf-8")
        return workflow_file
    except OSError as e:
        raise GitHubActionError(
            f"Failed to write workflow to {workflow_file}: {e}"
        ) from e


def _build_triggers(cfg: ActionConfig) -> str:
    """Build the YAML trigger section.

    Args:
        cfg: Action configuration.

    Returns:
        YAML string for the 'on:' section.
    """
    lines = ["on:"]
    branch_list = ", ".join(f'"{b}"' for b in cfg.branches)

    for trigger in cfg.triggers:
        if trigger in ("push", "pull_request"):
            lines.append(f"  {trigger}:")
            lines.append(f"    branches: [{branch_list}]")
        elif trigger == "workflow_dispatch":
            lines.append("  workflow_dispatch:")
        else:
            lines.append(f"  {trigger}:")

    return "\n".join(lines)


def _build_steps(cfg: ActionConfig) -> str:
    """Build the YAML steps section.

    Args:
        cfg: Action configuration.

    Returns:
        YAML string for the workflow steps, indented for jobs context.
    """
    steps: list[str] = []

    # Step 1: Checkout
    steps.append(
        "      - name: Checkout repository\n"
        "        uses: actions/checkout@v4\n"
        "        with:\n"
        "          fetch-depth: 0"
    )

    # Step 2: Setup Python
    steps.append(
        f"      - name: Set up Python {cfg.python_version}\n"
        "        uses: actions/setup-python@v5\n"
        "        with:\n"
        f"          python-version: \"{cfg.python_version}\""
    )

    # Step 3: Install codebase-md
    steps.append(
        "      - name: Install codebase-md\n"
        "        run: pip install codebase-md"
    )

    # Step 4: Scan
    steps.append(
        "      - name: Scan codebase\n"
        "        run: codebase scan ."
    )

    # Step 5: Generate
    format_list = " ".join(f"--format {f}" for f in cfg.formats) if cfg.formats else ""
    if format_list:
        # Generate each format individually
        gen_commands = "\n".join(f"          codebase generate . --format {f}" for f in cfg.formats)
        steps.append(
            "      - name: Generate context files\n"
            "        run: |\n"
            f"{gen_commands}"
        )
    else:
        steps.append(
            "      - name: Generate context files\n"
            "        run: codebase generate ."
        )

    # Step 6: Auto-commit (optional)
    if cfg.auto_commit:
        files_to_add = _get_output_files(cfg.formats)
        steps.append(
            "      - name: Commit generated files\n"
            "        run: |\n"
            f"          git config --local user.email \"codebase-md[bot]@users.noreply.github.com\"\n"
            f"          git config --local user.name \"codebase-md[bot]\"\n"
            f"          git add {files_to_add}\n"
            "          git diff --staged --quiet || git commit -m \"docs: update context files [codebase-md]\"\n"
            "          git push"
        )

    return "\n\n".join(steps)


def _get_output_files(formats: list[str]) -> str:
    """Map format names to output filenames for git add.

    Args:
        formats: List of format identifiers.

    Returns:
        Space-separated string of output filenames.
    """
    format_to_file: dict[str, str] = {
        "claude": "CLAUDE.md",
        "cursor": ".cursorrules",
        "agents": "AGENTS.md",
        "codex": "codex.md",
        "windsurf": ".windsurfrules",
        "generic": "PROJECT_CONTEXT.md",
    }
    files = [format_to_file.get(f, f) for f in formats]
    return " ".join(files)
