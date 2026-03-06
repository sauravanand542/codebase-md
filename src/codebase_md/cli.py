"""CLI entry point for codebase-md.

Provides all CLI commands for scanning, generating, and managing
codebase context files for AI coding tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from codebase_md import __app_name__, __version__

app = typer.Typer(
    name=__app_name__,
    help="The universal project brain — scan any codebase, generate context files for every AI coding tool.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"{__app_name__} v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
) -> None:
    """codebase-md: The universal project brain for AI coding tools."""


@app.command()
def init(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory to initialize."),
    ] = Path("."),
) -> None:
    """Initialize .codebase/ configuration in a project.

    Creates the .codebase/ directory with a default config.yaml
    containing generator preferences, scan settings, and hook options.
    """
    console.print(f"[bold green]Initializing[/bold green] .codebase/ in {path.resolve()}")

    from codebase_md.persistence.store import Store, StoreError

    try:
        store = Store(path.resolve())
        if store.is_initialized:
            console.print("[yellow]Already initialized.[/yellow] .codebase/ exists.")
            return
        codebase_dir = store.init()
        console.print(f"[bold green]Done![/bold green] Created {codebase_dir}")
    except StoreError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def scan(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory to scan."),
    ] = Path("."),
    depth: Annotated[
        str,
        typer.Option("--depth", "-d", help="Scan depth: 'full' or 'shallow' (no AST)."),
    ] = "full",
) -> None:
    """Scan a codebase and build the ProjectModel.

    Analyzes the project structure, detects languages and frameworks,
    parses dependencies, infers conventions, and saves the result
    to .codebase/project.json.
    """
    if depth not in ("full", "shallow"):
        console.print(
            f"[bold red]Error:[/bold red] Invalid depth '{depth}'. Must be 'full' or 'shallow'."
        )
        raise typer.Exit(code=1)
    console.print(f"[bold blue]Scanning[/bold blue] {path.resolve()} [dim](depth={depth})[/dim]")

    from codebase_md.scanner.engine import ScannerError, scan_project

    try:
        result = scan_project(path.resolve(), persist=True, depth=depth)
    except ScannerError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    # Display results
    model = result.model
    console.print(f"\n[bold green]Scan complete[/bold green] in {result.duration}s")
    console.print(f"  Project:      [bold]{model.name}[/bold]")
    console.print(f"  Architecture: {model.architecture.architecture_type.value}")
    console.print(f"  Languages:    {', '.join(model.languages) or 'none detected'}")
    console.print(f"  Modules:      {len(model.modules)}")
    console.print(f"  Dependencies: {len(model.dependencies)}")

    if model.architecture.entry_points:
        console.print(f"  Entry points: {', '.join(model.architecture.entry_points[:5])}")

    if result.warnings:
        console.print(f"\n[yellow]Warnings ({len(result.warnings)}):[/yellow]")
        for warning in result.warnings:
            console.print(f"  [dim]• {warning}[/dim]")

    console.print("\n  Saved to [dim].codebase/project.json[/dim]")


@app.command()
def generate(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory."),
    ] = Path("."),
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help="Specific format to generate (claude, cursor, agents, codex, windsurf, generic). Omit for all.",
        ),
    ] = None,
) -> None:
    """Generate context files from the last scan.

    Reads .codebase/project.json and produces output files
    (CLAUDE.md, .cursorrules, AGENTS.md, codex.md, .windsurfrules)
    based on the configured generators.
    """
    from codebase_md.generators import AVAILABLE_FORMATS, get_generator
    from codebase_md.generators.base import GeneratorError
    from codebase_md.persistence.store import ProjectNotFoundError, Store, StoreError

    resolved = path.resolve()
    format_msg = format if format else "all formats"
    console.print(f"[bold magenta]Generating[/bold magenta] {format_msg} for {resolved}")

    # Load project model from .codebase/project.json
    try:
        store = Store(resolved)
        model = store.read_project()
    except ProjectNotFoundError as e:
        console.print(
            "[bold red]Error:[/bold red] No scan data found. Run [bold]codebase scan[/bold] first."
        )
        raise typer.Exit(code=1) from e
    except StoreError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    # Determine which formats to generate
    if format:
        if format not in AVAILABLE_FORMATS:
            console.print(
                f"[bold red]Error:[/bold red] Unknown format '{format}'. "
                f"Available: {', '.join(AVAILABLE_FORMATS)}"
            )
            raise typer.Exit(code=1)
        formats_to_generate = [format]
    else:
        # Read config to see which generators are enabled, fallback to all
        try:
            config = store.read_config()
            configured = config.get("generators", AVAILABLE_FORMATS)
            formats_to_generate = (
                list(configured) if isinstance(configured, list) else list(AVAILABLE_FORMATS)
            )
        except StoreError:
            formats_to_generate = list(AVAILABLE_FORMATS)

    # Run each generator
    generated: list[str] = []
    for fmt in formats_to_generate:
        try:
            gen_class = get_generator(fmt)
            generator = gen_class()
            content = generator.generate(model)

            # Write output file to project root
            output_path = resolved / generator.output_filename
            output_path.write_text(content, encoding="utf-8")
            generated.append(generator.output_filename)
            console.print(f"  [green]✓[/green] {generator.output_filename}")
        except KeyError as e:
            console.print(f"  [yellow]⚠[/yellow] Skipping unknown format '{fmt}': {e}")
        except GeneratorError as e:
            console.print(f"  [red]✗[/red] {fmt}: {e}")
        except OSError as e:
            console.print(f"  [red]✗[/red] Failed to write {fmt}: {e}")

    if generated:
        console.print(
            f"\n[bold green]Done![/bold green] Generated {len(generated)} file(s): "
            f"{', '.join(generated)}"
        )
    else:
        console.print("\n[bold red]No files generated.[/bold red]")


@app.command()
def deps(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory."),
    ] = Path("."),
    upgrade: Annotated[
        str | None,
        typer.Option(
            "--upgrade",
            "-u",
            help="Show migration plan for a specific dependency.",
        ),
    ] = None,
    offline: Annotated[
        bool,
        typer.Option(
            "--offline",
            help="Skip registry queries (use cached data only).",
        ),
    ] = False,
) -> None:
    """Show dependency health dashboard.

    Displays current vs latest versions, health scores, and
    breaking change counts for all project dependencies.
    Use --upgrade <package> to see a detailed migration plan.
    """
    from codebase_md.depshift.analyzer import analyze_dependencies
    from codebase_md.persistence.store import ProjectNotFoundError, Store, StoreError

    resolved = path.resolve()

    # Load project model
    try:
        store = Store(resolved)
        model = store.read_project()
    except ProjectNotFoundError as e:
        console.print(
            "[bold red]Error:[/bold red] No scan data found. Run [bold]codebase scan[/bold] first."
        )
        raise typer.Exit(code=1) from e
    except StoreError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    if not model.dependencies:
        console.print("[yellow]No dependencies found.[/yellow]")
        return

    # Analyze dependencies
    console.print(
        f"[bold cyan]Analyzing[/bold cyan] {len(model.dependencies)} dependencies"
        f"{' [dim](offline)[/dim]' if offline else ''}..."
    )

    report = analyze_dependencies(
        model.dependencies,
        query_registries=not offline,
    )

    if upgrade:
        # Show migration plan for a specific dependency
        _show_migration_plan(resolved, report, upgrade, model)
    else:
        # Show health dashboard
        _show_health_dashboard(report)

    if report.warnings:
        console.print(f"\n[yellow]Warnings ({len(report.warnings)}):[/yellow]")
        for w in report.warnings:
            console.print(f"  [dim]• {w}[/dim]")


def _show_health_dashboard(report: Any) -> None:
    """Display the dependency health dashboard table.

    Args:
        report: The analyzed HealthReport.
    """
    from rich.table import Table

    table = Table(title="Dependency Health Dashboard", show_lines=False)
    table.add_column("Package", style="bold")
    table.add_column("Current", style="cyan")
    table.add_column("Latest", style="green")
    table.add_column("Health", justify="center")
    table.add_column("Score", justify="center")

    for dep in report.dependencies:
        # Health bar visualization
        filled = int(dep.health_score * 5)
        bar = "▓" * filled + "░" * (5 - filled)
        if dep.health_score >= 0.8:
            bar_styled = f"[green]{bar}[/green]"
        elif dep.health_score >= 0.5:
            bar_styled = f"[yellow]{bar}[/yellow]"
        else:
            bar_styled = f"[red]{bar}[/red]"

        latest_display = dep.latest or "?"

        table.add_row(
            dep.name,
            dep.version,
            latest_display,
            bar_styled,
            f"{dep.health_score:.1f}",
        )

    console.print()
    console.print(table)

    # Summary line
    s = report.summary
    console.print(
        f"\n  [bold]{s.total}[/bold] deps: "
        f"[green]{s.healthy} healthy[/green], "
        f"[yellow]{s.outdated} outdated[/yellow], "
        f"[red]{s.deprecated} deprecated[/red], "
        f"[dim]{s.unknown} unknown[/dim]"
    )
    console.print(f"  Average health: [bold]{s.average_score:.2f}[/bold] / 1.00")


def _show_migration_plan(
    root_path: Path,
    report: Any,
    package_name: str,
    model: Any,
) -> None:
    """Show a detailed migration plan for a specific dependency.

    Args:
        root_path: Project root.
        report: The analyzed HealthReport.
        package_name: Name of the dependency to upgrade.
        model: The ProjectModel for usage mapping.
    """
    from codebase_md.depshift.usage_mapper import map_dependency_usage
    from codebase_md.depshift.version_differ import compare_versions, format_version_diff

    # Find the dependency
    target = None
    for dep in report.dependencies:
        if dep.name == package_name:
            target = dep
            break

    if not target:
        console.print(f"[bold red]Error:[/bold red] Dependency '{package_name}' not found.")
        console.print("Available: " + ", ".join(d.name for d in report.dependencies))
        return

    console.print(f"\n[bold cyan]Migration Plan:[/bold cyan] {target.name}")

    if not target.latest:
        console.print("[yellow]  Latest version unknown — run without --offline.[/yellow]")
        return

    # Version diff
    from codebase_md.depshift.analyzer import clean_version

    current_clean = clean_version(target.version)
    diff = compare_versions(current_clean, target.latest)
    console.print(f"  Version: {format_version_diff(diff)}")

    if not diff.is_behind:
        console.print("  [green]Already up to date![/green]")
        return

    # Usage mapping
    console.print("\n  [bold]Your code impact:[/bold]")
    usage_maps = map_dependency_usage(
        root_path,
        [target.name],
        target.ecosystem,
    )

    if usage_maps and usage_maps[0].locations:
        usage = usage_maps[0]
        for loc in usage.locations[:10]:  # Show max 10 locations
            console.print(
                f"    ├── [dim]{loc.file_path}:{loc.line_number}[/dim]  → {loc.line_content[:60]}"
            )
        if len(usage.locations) > 10:
            console.print(f"    └── ... and {len(usage.locations) - 10} more locations")
        console.print(
            f"\n  Files affected: [bold]{len(set(loc.file_path for loc in usage.locations))}[/bold]"
        )
        console.print(f"  Import count:   [bold]{usage.import_count}[/bold]")
    else:
        console.print("    [dim]No direct imports found in source files.[/dim]")

    # Risk assessment
    risk = "Low"
    if diff.breaking_likely:
        risk = "High" if diff.major_diff > 1 else "Medium"

    console.print(f"\n  Risk:  [bold]{risk}[/bold]")
    console.print(f"  Type:  {diff.upgrade_type} upgrade")


# --- Decisions subcommand group ---

decisions_app = typer.Typer(
    name="decisions",
    help="Manage architectural decision records (ADRs).",
)
app.add_typer(decisions_app)


@decisions_app.command("add")
def decisions_add(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory."),
    ] = Path("."),
) -> None:
    """Interactively record a new architectural decision."""
    from datetime import UTC, datetime

    from codebase_md.model.decision import DecisionRecord
    from codebase_md.persistence.decisions import DecisionLog, DecisionLogError

    resolved = path.resolve()
    console.print("[bold green]Record a new architectural decision[/bold green]\n")

    # Interactive prompts
    title = typer.prompt("Decision title (e.g. 'Use PostgreSQL')")
    context_text = typer.prompt("Context (why was a decision needed?)")
    choice = typer.prompt("Choice (what was decided?)")

    # Alternatives — comma-separated
    alt_input = typer.prompt(
        "Alternatives considered (comma-separated, or press Enter to skip)",
        default="",
    )
    alternatives = [a.strip() for a in alt_input.split(",") if a.strip()] if alt_input else []

    # Consequences — comma-separated
    cons_input = typer.prompt(
        "Consequences/trade-offs (comma-separated, or press Enter to skip)",
        default="",
    )
    consequences = [c.strip() for c in cons_input.split(",") if c.strip()] if cons_input else []

    decision = DecisionRecord(
        date=datetime.now(tz=UTC),
        title=title,
        context=context_text,
        choice=choice,
        alternatives=alternatives,
        consequences=consequences,
    )

    try:
        log = DecisionLog(resolved)
        log.add_decision(decision)
        console.print(f"\n[bold green]Done![/bold green] Decision recorded: [bold]{title}[/bold]")
    except DecisionLogError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@decisions_app.command("list")
def decisions_list(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory."),
    ] = Path("."),
) -> None:
    """List all recorded architectural decisions."""
    from rich.table import Table

    from codebase_md.persistence.decisions import DecisionLog, DecisionLogError

    resolved = path.resolve()

    try:
        log = DecisionLog(resolved)
        records = log.list_decisions()
    except DecisionLogError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    if not records:
        console.print(
            "[yellow]No decisions recorded yet.[/yellow] Use [bold]codebase decisions add[/bold] to record one."
        )
        return

    table = Table(title=f"Architectural Decisions ({len(records)})", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Title", style="bold")
    table.add_column("Choice", style="green")
    table.add_column("Alternatives", style="dim")

    for i, record in enumerate(records, 1):
        date_str = record.date.strftime("%Y-%m-%d")
        alts = ", ".join(record.alternatives) if record.alternatives else "—"
        table.add_row(str(i), date_str, record.title, record.choice, alts)

    console.print()
    console.print(table)


@decisions_app.command("remove")
def decisions_remove(
    index: Annotated[
        int,
        typer.Argument(help="Decision number to remove (1-based, from 'decisions list')."),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project root directory."),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Remove an architectural decision by its index number."""
    from codebase_md.persistence.decisions import DecisionLog, DecisionLogError

    resolved = path.resolve()

    try:
        log = DecisionLog(resolved)
        records = log.list_decisions()
    except DecisionLogError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    if not records:
        console.print("[yellow]No decisions to remove.[/yellow]")
        return

    if index < 1 or index > len(records):
        console.print(
            f"[bold red]Error:[/bold red] Invalid index {index}. Valid range: 1-{len(records)}."
        )
        raise typer.Exit(code=1)

    target = records[index - 1]
    console.print(f"Decision #{index}: [bold]{target.title}[/bold] — {target.choice}")

    if not force:
        confirm = typer.confirm("Remove this decision?")
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    # Remove using public API
    try:
        log.remove_decision(index)
        console.print(f"[bold green]Removed[/bold green] decision #{index}: {target.title}")
    except DecisionLogError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e


@app.command()
def watch(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory to watch."),
    ] = Path("."),
    interval: Annotated[
        int,
        typer.Option("--interval", "-i", help="Poll interval in seconds."),
    ] = 5,
) -> None:
    """Watch for file changes and regenerate context files.

    Monitors the project for changes by polling at the specified interval.
    When source files are modified, automatically re-scans and regenerates
    output files. Press Ctrl+C to stop.
    """
    import time

    from codebase_md.persistence.store import Store, StoreError
    from codebase_md.scanner.differ import compute_diff
    from codebase_md.scanner.engine import ScannerError, scan_project

    resolved = path.resolve()
    console.print(
        f"[bold yellow]Watching[/bold yellow] {resolved} "
        f"[dim](interval: {interval}s, Ctrl+C to stop)[/dim]"
    )

    # Ensure we have an initial scan
    try:
        store = Store(resolved)
        store.read_project()
    except Exception:
        console.print("[dim]No initial scan found — running first scan...[/dim]")
        try:
            scan_project(resolved, persist=True)
            console.print("[green]Initial scan complete.[/green]")
        except ScannerError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from e

    try:
        while True:
            time.sleep(interval)

            # Run a fresh scan without persisting
            try:
                result = scan_project(resolved, persist=False)
            except ScannerError:
                continue

            # Compare with stored model
            try:
                store = Store(resolved)
                old_model = store.read_project()
            except StoreError:
                continue

            diff_result = compute_diff(old_model, result.model)

            if diff_result.has_changes:
                console.print(
                    f"\n[bold yellow]Changes detected:[/bold yellow] {diff_result.summary}"
                )

                # Re-scan and persist
                try:
                    scan_project(resolved, persist=True)
                except ScannerError as e:
                    console.print(f"[red]Re-scan failed:[/red] {e}")
                    continue

                # Regenerate all formats
                from codebase_md.generators import AVAILABLE_FORMATS, get_generator
                from codebase_md.generators.base import GeneratorError

                try:
                    model = store.read_project()
                    config = store.read_config()
                    formats = config.get("generators", AVAILABLE_FORMATS)
                    if not isinstance(formats, list):
                        formats = list(AVAILABLE_FORMATS)

                    generated: list[str] = []
                    for fmt in formats:
                        try:
                            gen_class = get_generator(fmt)
                            generator = gen_class()
                            content = generator.generate(model)
                            output_path = resolved / generator.output_filename
                            output_path.write_text(content, encoding="utf-8")
                            generated.append(generator.output_filename)
                        except (KeyError, GeneratorError, OSError):
                            pass

                    if generated:
                        console.print(f"  [green]Regenerated:[/green] {', '.join(generated)}")
                except StoreError:
                    console.print("  [red]Failed to regenerate.[/red]")

    except KeyboardInterrupt:
        console.print("\n[bold]Stopped watching.[/bold]")


@app.command()
def diff(
    path: Annotated[
        Path,
        typer.Argument(help="Project root directory."),
    ] = Path("."),
) -> None:
    """Show what changed since the last scan.

    Compares the current codebase state with the persisted
    .codebase/project.json and highlights additions, removals,
    and modifications.
    """
    from codebase_md.persistence.store import ProjectNotFoundError, Store, StoreError
    from codebase_md.scanner.differ import compute_diff, format_diff
    from codebase_md.scanner.engine import ScannerError, scan_project

    resolved = path.resolve()
    console.print(f"[bold cyan]Diff[/bold cyan] since last scan for {resolved}")

    # Load the previous scan
    try:
        store = Store(resolved)
        old_model = store.read_project()
    except ProjectNotFoundError as e:
        console.print(
            "[bold red]Error:[/bold red] No previous scan found. Run [bold]codebase scan[/bold] first."
        )
        raise typer.Exit(code=1) from e
    except StoreError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    # Run a fresh scan (without persisting — we just want to compare)
    console.print("[dim]Running fresh scan...[/dim]")
    try:
        result = scan_project(resolved, persist=False)
    except ScannerError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    new_model = result.model

    # Compute diff
    diff_result = compute_diff(old_model, new_model)

    # Display
    console.print()
    if not diff_result.has_changes:
        console.print("[bold green]No changes[/bold green] since last scan.")
    else:
        output = format_diff(diff_result)
        console.print(output)
        console.print(f"\n[dim]Summary: {diff_result.summary}[/dim]")


@app.command()
def hooks(
    action: Annotated[
        str,
        typer.Argument(help="Action: 'install', 'remove', or 'status'."),
    ] = "install",
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project root directory."),
    ] = Path("."),
) -> None:
    """Install, remove, or check status of git hooks for auto-regeneration.

    Installs post-commit and/or pre-push hooks that automatically re-scan
    and regenerate context files after git operations. Hook configuration
    is read from .codebase/config.yaml.
    """
    from codebase_md.integrations.git_hooks import (
        GitHooksError,
        install_all_hooks,
        list_installed_hooks,
        remove_all_hooks,
    )

    resolved = path.resolve()

    if action == "install":
        console.print(f"[bold green]Installing[/bold green] git hooks in {resolved}")
        try:
            installed = install_all_hooks(resolved)
            if installed:
                for hook_path in installed:
                    console.print(f"  [green]✓[/green] {hook_path.name}")
                console.print(
                    f"\n[bold green]Done![/bold green] Installed {len(installed)} hook(s)."
                )
            else:
                console.print("[yellow]No hooks configured to install.[/yellow]")
        except GitHooksError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from e

    elif action == "remove":
        console.print(f"[bold red]Removing[/bold red] git hooks from {resolved}")
        try:
            removed = remove_all_hooks(resolved)
            if removed:
                for hook_type in removed:
                    console.print(f"  [green]✓[/green] Removed {hook_type.value}")
                console.print(f"\n[bold green]Done![/bold green] Removed {len(removed)} hook(s).")
            else:
                console.print("[yellow]No codebase-md hooks found to remove.[/yellow]")
        except GitHooksError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from e

    elif action == "status":
        console.print(f"[bold cyan]Hook status[/bold cyan] for {resolved}")
        try:
            installed_hooks = list_installed_hooks(resolved)
            if installed_hooks:
                for hook_type in installed_hooks:
                    console.print(f"  [green]✓[/green] {hook_type.value} — installed")
            else:
                console.print("  [dim]No codebase-md hooks installed.[/dim]")
        except GitHooksError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(code=1) from e

    else:
        console.print(
            f"[bold red]Error:[/bold red] Unknown action '{action}'. "
            "Use 'install', 'remove', or 'status'."
        )
        raise typer.Exit(code=1)


@app.command()
def context(
    query: Annotated[
        str,
        typer.Argument(help="Query or question to find relevant context for."),
    ],
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Project root directory."),
    ] = Path("."),
    max_chunks: Annotated[
        int,
        typer.Option("--max", "-m", help="Maximum number of context chunks to return."),
    ] = 5,
    min_score: Annotated[
        float,
        typer.Option("--min-score", help="Minimum relevance score threshold."),
    ] = 0.1,
    compact: Annotated[
        bool,
        typer.Option("--compact", "-c", help="Output compact format (content only, no scores)."),
    ] = False,
) -> None:
    """Query relevant project context.

    Routes the most relevant project knowledge to your query using
    smart chunking and relevance ranking. Useful for getting focused
    context about specific aspects of the project (architecture,
    dependencies, a specific module, conventions, etc.).
    """
    from codebase_md.context.router import (
        RoutingError,
        format_routed_context,
        format_routed_context_compact,
        route_context,
    )
    from codebase_md.persistence.store import ProjectNotFoundError, Store, StoreError

    resolved = path.resolve()
    console.print(f"[bold cyan]Routing context[/bold cyan] for: [italic]{query}[/italic]")

    # Load project model
    try:
        store = Store(resolved)
        model = store.read_project()
    except ProjectNotFoundError as e:
        console.print(
            "[bold red]Error:[/bold red] No scan data found. Run [bold]codebase scan[/bold] first."
        )
        raise typer.Exit(code=1) from e
    except StoreError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    # Route context
    try:
        result = route_context(
            query=query,
            model=model,
            max_chunks=max_chunks,
            min_score=min_score,
        )
    except RoutingError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from e

    if not result.chunks:
        console.print(
            f"\n[yellow]No relevant context found[/yellow] for '{query}' (threshold: {min_score})"
        )
        return

    # Display results
    output = format_routed_context_compact(result) if compact else format_routed_context(result)

    console.print()
    console.print(output)

    # Summary
    console.print(
        f"\n[dim]Returned {len(result.chunks)} of {result.total_chunks} chunks "
        f"(top score: {result.max_score:.2f})[/dim]"
    )
