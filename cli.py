#!/usr/bin/env python3
"""
DistillNews CLI — single entry point for the entire pipeline.

Usage:
    ./cli.py              Launch the TUI dashboard (default)
    ./cli.py tui           Launch the TUI dashboard (explicit)
    ./cli.py fetch         Fetch data from all enabled sources
    ./cli.py scrape        Run the web scraping pipeline
    ./cli.py generate      Run article generation / LLM extraction
    ./cli.py pipeline      Run full pipeline: fetch → scrape → generate
    ./cli.py articles      List processed articles
    ./cli.py status        Show configuration and system status
    ./cli.py serve         Start the FastAPI server
"""

import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so project imports work
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


# ── Main group ──────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """DistillNews — AI-Powered News Aggregation Pipeline."""
    if ctx.invoked_subcommand is None:
        _launch_tui()


# ── TUI ─────────────────────────────────────────────────────────────────────

@cli.command()
def tui():
    """Launch the interactive TUI dashboard."""
    _launch_tui()


def _launch_tui():
    """Start the Textual TUI application."""
    from pipeline.tui.app import DistillNewsApp
    app = DistillNewsApp()
    app.run()


# ── Fetch ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--source", "-s",
    multiple=True,
    help="Specific source(s) to fetch (e.g. reddit, gnews). Repeatable.",
)
def fetch(source):
    """Fetch data from news API sources."""
    from pipeline.runner import PipelineRunner

    sources = list(source) if source else None
    label = ", ".join(sources) if sources else "all enabled sources"
    console.print(f"\n[bold cyan]⟫ Fetching from {label}…[/bold cyan]\n")

    runner = PipelineRunner()
    runner.run_fetch(sources=sources)

    console.print("\n[bold green]✓ Fetch complete.[/bold green]")


# ── Scrape ──────────────────────────────────────────────────────────────────

@cli.command()
def scrape():
    """Run the web scraping pipeline."""
    console.print("\n[bold cyan]⟫ Running web scraper…[/bold cyan]\n")

    from pipeline.runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_scrape()

    console.print("\n[bold green]✓ Scrape complete.[/bold green]")


# ── Generate ────────────────────────────────────────────────────────────────

@cli.command()
def generate():
    """Run article generation (LLM extraction)."""
    console.print("\n[bold cyan]⟫ Running article generation…[/bold cyan]\n")

    from pipeline.runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_generate()

    console.print("\n[bold green]✓ Generation complete.[/bold green]")


# ── Embed ───────────────────────────────────────────────────────────────────

@cli.command()
def embed():
    """Run article embedding stage."""
    console.print("\n[bold cyan]⟫ Running article embedding stage…[/bold cyan]\n")

    from pipeline.runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_embed()

    console.print("\n[bold green]✓ Embedding complete.[/bold green]")


# ── Pipeline (full) ────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--source", "-s",
    multiple=True,
    help="Specific source(s) to fetch (e.g. reddit, gnews). Repeatable.",
)
def pipeline(source):
    """Run the full pipeline: fetch → scrape → generate → embed."""
    sources = list(source) if source else None

    console.print(Panel(
        "[bold]fetch → scrape → generate → embed[/bold]",
        title="[cyan]Full Pipeline[/cyan]",
        border_style="cyan",
    ))

    from pipeline.runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_all(sources=sources)

    console.print("\n[bold green]✓ Full pipeline complete.[/bold green]")


# ── Articles ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--id", "article_id", default=None, help="View a specific article by ID (hash prefix).")
@click.option("--limit", "-n", default=25, help="Number of articles to display.")
def articles(article_id, limit):
    """List or view processed articles."""
    from service.db import FileStore
    import json

    if article_id:
        # View specific article
        article = FileStore.load_processed_article(article_id)
        if not article:
            # Try prefix match
            files = FileStore.list_processed_files()
            matches = [f for f in files if f.stem.startswith(article_id)]
            if len(matches) == 1:
                article = FileStore.read_json(matches[0])
            elif len(matches) > 1:
                console.print(f"[yellow]Ambiguous ID prefix '{article_id}', matches {len(matches)} articles.[/yellow]")
                for m in matches[:10]:
                    console.print(f"  {m.stem}")
                return
            else:
                console.print(f"[red]Article not found: {article_id}[/red]")
                return

        console.print(Panel(
            f"[bold]{article.get('title', 'Untitled')}[/bold]\n\n"
            f"[dim]Category:[/dim] {article.get('category', 'N/A')}\n"
            f"[dim]Date:[/dim]     {article.get('publication_date', 'N/A')}\n"
            f"[dim]Location:[/dim] {article.get('location', 'N/A')}\n\n"
            f"{article.get('content', article.get('summary', 'No content.'))}",
            title="[cyan]Article[/cyan]",
            border_style="blue",
            padding=(1, 2),
        ))
        return

    # List articles
    files = FileStore.list_processed_files()
    if not files:
        console.print("[dim]No processed articles found.[/dim]")
        return

    table = Table(
        title=f"Processed Articles ({len(files)} total)",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=False,
        pad_edge=True,
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Title", style="bold", max_width=50)
    table.add_column("Category", style="green", width=14)
    table.add_column("Date", style="blue", width=12)
    table.add_column("ID", style="dim", width=12)

    for i, filepath in enumerate(files[-limit:], 1):
        try:
            data = FileStore.read_json(filepath)
            table.add_row(
                str(i),
                (data.get("title", "Untitled") or "Untitled")[:50],
                data.get("category", "—"),
                str(data.get("publication_date", "—"))[:10],
                filepath.stem[:12] + "…",
            )
        except Exception:
            table.add_row(str(i), "[red]Error reading[/red]", "—", "—", filepath.stem[:12])

    console.print(table)


# ── Status ──────────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show configuration, enabled sources, and article counts."""
    from config import config
    from service.db import FileStore
    from pipeline.runner import SOURCE_REGISTRY

    # Header
    console.print(Panel(
        "[bold cyan]DistillNews[/bold cyan] System Status",
        border_style="cyan",
    ))

    # Sources table
    src_table = Table(
        title="Pipeline Sources",
        box=box.ROUNDED,
        border_style="blue",
    )
    src_table.add_column("Source", style="bold")
    src_table.add_column("Status", justify="center")

    for name in sorted(SOURCE_REGISTRY.keys()):
        enabled = config.is_source_enabled(name)
        icon = "[green]✓ enabled[/green]" if enabled else "[dim]✗ disabled[/dim]"
        src_table.add_row(name, icon)

    # Also check 'scrape'
    scrape_enabled = config.is_source_enabled("scrape")
    src_table.add_row("scrape", "[green]✓ enabled[/green]" if scrape_enabled else "[dim]✗ disabled[/dim]")

    console.print(src_table)

    # Article stats
    files = FileStore.list_processed_files()
    console.print(f"\n  [bold]Processed articles:[/bold] {len(files)}")
    console.print(f"  [bold]Data directory:[/bold]     {FileStore.get_root()}")

    # Provider info
    console.print(f"\n  [bold]Agent provider:[/bold]    {config.AGENT_PROVIDER}")
    console.print(f"  [bold]RAG backend:[/bold]       {config.RAG_BACKEND}")
    console.print(f"  [bold]Embedding provider:[/bold] {config.EMBEDDING_PROVIDER}")
    console.print()


# ── Serve ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind host.")
@click.option("--port", "-p", default=8000, type=int, help="Bind port.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload.")
def serve(host, port, do_reload):
    """Start the FastAPI server."""
    import uvicorn

    console.print(f"\n[bold cyan]⟫ Starting server on {host}:{port}…[/bold cyan]\n")
    uvicorn.run("server.app:app", host=host, port=port, reload=do_reload)


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
