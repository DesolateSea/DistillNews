#!/usr/bin/env python3
"""
DistillNews CLI — entry point for launching the interactive TUI dashboard.

Usage:
    python pipeline/cli.py              Launch the TUI dashboard (default)
    python pipeline/cli.py tui          Launch the TUI dashboard (explicit)

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


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
