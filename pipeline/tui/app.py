"""
Interactive Terminal User Interface (TUI) for DistillNews Ingestion Pipeline.
"""
import os
import sys
from pathlib import Path

def print_banner():
    print("=" * 60)
    print(" 📰 DistillNews Pipeline Terminal User Interface (TUI)")
    print("=" * 60)

def show_status():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    
    raw_count = len(list(raw_dir.glob("**/*.*"))) if raw_dir.exists() else 0
    processed_count = len(list(processed_dir.glob("*.json"))) if processed_dir.exists() else 0
    
    print("\n--- Pipeline Status ---")
    print(f"📁 Raw Data Path:       {raw_dir}")
    print(f"📁 Processed Data Path: {processed_dir}")
    print(f"📄 Raw Files Scraped:   {raw_count}")
    print(f"📰 Processed Articles:  {processed_count}")
    print("-----------------------\n")

def run_menu():
    while True:
        print_banner()
        show_status()
        print("Select an operation:")
        print("  [1] Run Web Scraper")
        print("  [2] Run News Extraction")
        print("  [3] Run Full Generation Pipeline")
        print("  [4] Exit TUI")
        print()
        
        choice = input("Enter choice [1-4]: ").strip()
        if choice == "1":
            from pipeline.scrape import scrape_all
            print("\n🚀 Executing Scraper...")
            scrape_all()
            input("\nPress Enter to continue...")
        elif choice == "2":
            from pipeline.extraction import extract_news
            print("\n🚀 Executing Extractor...")
            extract_news()
            input("\nPress Enter to continue...")
        elif choice == "3":
            from pipeline.generate import run_pipeline
            print("\n🚀 Executing Full Pipeline...")
            run_pipeline()
            input("\nPress Enter to continue...")
        elif choice == "4" or choice.lower() == "q":
            print("\nExiting TUI. Goodbye!\n")
            break
        else:
            print("\n⚠️ Invalid choice, please try again.\n")

def main():
    try:
        run_menu()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled. Exiting TUI.")

if __name__ == "__main__":
    main()
