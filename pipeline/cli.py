#!/usr/bin/env python3
"""
DistillNews CLI — single entry point for the entire pipeline.

Usage:
    python pipeline/cli.py              Launch the TUI dashboard (default)
    python pipeline/cli.py tui          Launch the TUI dashboard (explicit)
    python pipeline/cli.py fetch        Fetch data from all enabled sources
    python pipeline/cli.py scrape       Run the web scraping pipeline
    python pipeline/cli.py extract      Run article extraction (LLM)
    python pipeline/cli.py generate     Run article generation / LLM extraction
    python pipeline/cli.py embed        Run article embedding stage
    python pipeline/cli.py pipeline     Run full pipeline: fetch → scrape → generate → embed
    python pipeline/cli.py articles     List processed articles
    python pipeline/cli.py status       Show configuration and system status
    python pipeline/cli.py serve        Start the FastAPI server

Options:
    --storage, -st [file|azure]         Override ARTICLE_STORE_BACKEND
"""

import os
import sys
from pathlib import Path

# Ensure the project root directory is on sys.path so project imports work
_root_dir = str(Path(__file__).resolve().parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def _apply_storage(storage: str | None):
    if storage:
        os.environ["ARTICLE_STORE_BACKEND"] = storage.lower()


# ── Main group ──────────────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
@click.pass_context
def cli(ctx, storage):
    """DistillNews — AI-Powered News Aggregation Pipeline."""
    _apply_storage(storage)
    if ctx.invoked_subcommand is None:
        _launch_tui()


# ── TUI ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def tui(storage):
    """Launch the interactive TUI dashboard."""
    _apply_storage(storage)
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


# ── Extract ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def extract(storage):
    """Run article extraction (LLM extraction)."""
    _apply_storage(storage)
    console.print("\n[bold cyan]⟫ Running article extraction…[/bold cyan]\n")

    from pipeline.extraction import extract_news
    extract_news()

    console.print("\n[bold green]✓ Extraction complete.[/bold green]")


# ── Generate ────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def generate(storage):
    """Run article generation (LLM extraction)."""
    _apply_storage(storage)
    console.print("\n[bold cyan]⟫ Running article generation…[/bold cyan]\n")

    from pipeline.runner import PipelineRunner
    runner = PipelineRunner()
    runner.run_generate()

    console.print("\n[bold green]✓ Generation complete.[/bold green]")


# ── Embed ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def embed(storage):
    """Run article embedding stage."""
    _apply_storage(storage)
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
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def pipeline(source, storage):
    """Run the full pipeline: fetch → scrape → generate → embed."""
    _apply_storage(storage)
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
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def articles(article_id, limit, storage):
    """List or view processed articles."""
    _apply_storage(storage)
    from service.db import create_article_store
    import json

    article_store = create_article_store()

    if article_id:
        # View specific article
        article = article_store.load_article(article_id)
        if not article:
            # Try prefix match
            all_articles = article_store.list_articles()
            matches = [a for a in all_articles if a.get("id", "").startswith(article_id)]
            if len(matches) == 1:
                article = article_store.load_article(matches[0]["id"])
            elif len(matches) > 1:
                console.print(f"[yellow]Ambiguous ID prefix '{article_id}', matches {len(matches)} articles.[/yellow]")
                for m in matches[:10]:
                    console.print(f"  {m.get('id', '')}")
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
    all_articles = article_store.list_articles()
    if not all_articles:
        console.print("[dim]No processed articles found.[/dim]")
        return

    table = Table(
        title=f"Processed Articles ({len(all_articles)} total) [{os.getenv('ARTICLE_STORE_BACKEND', 'file')}]",
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

    for i, data in enumerate(all_articles[-limit:], 1):
        try:
            table.add_row(
                str(i),
                (data.get("title", "Untitled") or "Untitled")[:50],
                data.get("category", "—"),
                str(data.get("publication_date", "—"))[:10],
                data.get("id", "")[:12] + "…",
            )
        except Exception:
            table.add_row(str(i), "[red]Error reading[/red]", "—", "—", data.get("id", "")[:12])

    console.print(table)


# ── Status ──────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def status(storage):
    """Show configuration, enabled sources, and article counts."""
    _apply_storage(storage)
    from config import config
    from service.db import FileStore, create_article_store
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
    article_store = create_article_store()
    articles = article_store.list_articles()
    console.print(f"\n  [bold]Processed articles:[/bold] {len(articles)}")
    console.print(f"  [bold]Data directory:[/bold]     {FileStore.get_root()}")

    # Provider info
    console.print(f"\n  [bold]Agent provider:[/bold]      {config.AGENT_PROVIDER}")
    console.print(f"  [bold]RAG backend:[/bold]         {config.RAG_BACKEND}")
    console.print(f"  [bold]Embedding provider:[/bold]   {config.EMBEDDING_PROVIDER}")
    console.print(f"  [bold]Article store:[/bold]        {config.ARTICLE_STORE_BACKEND}")
    console.print()


# ── Serve ───────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind host.")
@click.option("--port", "-p", default=8000, type=int, help="Bind port.")
@click.option("--reload", "do_reload", is_flag=True, help="Enable auto-reload.")
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def serve(host, port, do_reload, storage):
    """Start the FastAPI server."""
    _apply_storage(storage)
    import uvicorn

    console.print(f"\n[bold cyan]⟫ Starting server on {host}:{port} (Storage: {config.ARTICLE_STORE_BACKEND})…[/bold cyan]\n")
    uvicorn.run("server.app:app", host=host, port=port, reload=do_reload)


# ── Clear Cache ─────────────────────────────────────────────────────────────

@cli.command("clear-cache")
@click.option(
    "--storage", "-st",
    type=click.Choice(["file", "azure"], case_sensitive=False),
    default=None,
    help="Override article storage backend (file or azure).",
)
def clear_cache(storage):
    """Flush Redis cache and re-index all article metadata into Redis."""
    _apply_storage(storage)
    import asyncio
    from service.db import RedisHandle
    from service.articles import prime_redis_indexes

    console.print("\n[bold cyan]⟫ Flushing Redis cache & re-indexing articles…[/bold cyan]\n")

    async def _run_flush():
        try:
            await RedisHandle.connect()
            r = RedisHandle.client()
            await r.flushdb()
            console.print("[green]✓ Redis database flushed (FLUSHDB).[/green]")
            await prime_redis_indexes(force=True)
            console.print("[green]✓ Redis ZSETs & Hashes re-indexed with updated article metadata![/green]")
            await RedisHandle.disconnect()
        except Exception as e:
            console.print(f"[bold red]❌ Redis clear failed:[/bold red] {e}")

    asyncio.run(_run_flush())
    console.print("\n[bold green]✓ Cache cleared successfully.[/bold green]")


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
