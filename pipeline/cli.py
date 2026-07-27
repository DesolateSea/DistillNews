#!/usr/bin/env python3
"""
Independent CLI runner for the DistillNews Ingestion Pipeline and TUI.
"""
import sys
import argparse
from pathlib import Path

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def run_scrape(args):
    from pipeline.scrape import scrape_all
    print("🚀 Starting news scraper...")
    scrape_all()
    print("✅ Scraping complete.")

def run_extract(args):
    from pipeline.extraction import extract_news
    print("🚀 Starting news extraction...")
    extract_news()
    print("✅ Extraction complete.")

def run_generate(args):
    from pipeline.generate import run_pipeline
    print("🚀 Starting full news pipeline generation...")
    run_pipeline()
    print("✅ Pipeline generation complete.")

def run_tui(args):
    from pipeline.tui.app import main as tui_main
    tui_main()

def main():
    parser = argparse.ArgumentParser(
        description="DistillNews Pipeline & TUI Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Run web scraping for target sources")
    scrape_parser.set_defaults(func=run_scrape)

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract structured news articles using LLM agents")
    extract_parser.set_defaults(func=run_extract)

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Run full pipeline: scraper -> extractor -> generator")
    gen_parser.set_defaults(func=run_generate)

    # TUI command
    tui_parser = subparsers.add_parser("tui", help="Launch the interactive Terminal User Interface (TUI)")
    tui_parser.set_defaults(func=run_tui)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
