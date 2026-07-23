"""
Pipeline Logger — colored, structured terminal output for pipeline stages.

Zero external dependencies — uses ANSI escape codes directly.
Automatically truncates long strings to keep the terminal readable.
"""

import time
import textwrap
from contextlib import contextmanager


# ── ANSI color / style codes ────────────────────────────────────────────────

class _C:
    """ANSI escape helpers."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Foreground
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

    # Background (for badges)
    BG_GREEN   = "\033[42m"
    BG_RED     = "\033[41m"
    BG_BLUE    = "\033[44m"
    BG_YELLOW  = "\033[43m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN    = "\033[46m"


# ── Truncation ──────────────────────────────────────────────────────────────

MAX_INLINE = 120  # max chars for a single-line value before truncation


def truncate(text: str, max_len: int = MAX_INLINE) -> str:
    """Truncate *text* to *max_len* characters, appending '…' if trimmed."""
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\n", " ").replace("\r", "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


# ── Badge builders ──────────────────────────────────────────────────────────

def _badge(label: str, bg: str, fg: str = _C.WHITE) -> str:
    return f"{bg}{fg}{_C.BOLD} {label} {_C.RESET}"


# ── Logger class ────────────────────────────────────────────────────────────

class PipelineLogger:
    """Structured, colored logger for DistillNews pipeline stages."""

    # Pre-built badges
    _BADGES = {
        "scrape":   _badge("SCRAPE",   _C.BG_CYAN,    _C.WHITE),
        "fetch":    _badge("FETCH",    _C.BG_BLUE,    _C.WHITE),
        "parse":    _badge("PARSE",    _C.BG_MAGENTA, _C.WHITE),
        "ai":       _badge("  AI  ",   _C.BG_YELLOW,  _C.WHITE),
        "save":     _badge(" SAVE ",   _C.BG_GREEN,   _C.WHITE),
        "skip":     _badge(" SKIP ",   _C.BG_BLUE,    _C.WHITE),
        "ok":       _badge("  OK  ",   _C.BG_GREEN,   _C.WHITE),
        "fail":     _badge(" FAIL ",   _C.BG_RED,     _C.WHITE),
        "warn":     _badge(" WARN ",   _C.BG_YELLOW,  _C.WHITE),
        "info":     _badge(" INFO ",   _C.BG_BLUE,    _C.WHITE),
        "chat":     _badge(" CHAT ",   _C.BG_MAGENTA, _C.WHITE),
        "rag":      _badge(" RAG  ",   _C.BG_CYAN,    _C.WHITE),
        "db":       _badge("  DB  ",   _C.BG_GREEN,   _C.WHITE),
    }

    # ── core print ──────────────────────────────────────────────────────

    @staticmethod
    def _print(badge_key: str, message: str, detail: str | None = None):
        badge = PipelineLogger._BADGES.get(badge_key, f"[{badge_key.upper()}]")
        line = f"{badge} {message}"
        if detail is not None:
            line += f"  {_C.DIM}{truncate(detail)}{_C.RESET}"
        print(line)

    # ── public helpers ──────────────────────────────────────────────────

    # --- Scraping / Fetching ---

    @staticmethod
    def scrape_start(url: str, dest: str | None = None):
        msg = f"{_C.CYAN}Scraping{_C.RESET} {_C.BOLD}{truncate(url, 80)}{_C.RESET}"
        PipelineLogger._print("scrape", msg, f"→ {dest}" if dest else None)

    @staticmethod
    def scrape_skip(url: str, reason: str = "already scraped"):
        PipelineLogger._print("skip", f"{_C.GRAY}{truncate(url, 80)}{_C.RESET}  ({reason})")

    @staticmethod
    def fetch_start(source: str, query: str | None = None):
        msg = f"{_C.BLUE}Fetching from {_C.BOLD}{source}{_C.RESET}"
        PipelineLogger._print("fetch", msg, query)

    @staticmethod
    def fetch_done(source: str, count: int):
        PipelineLogger._print("ok", f"{_C.GREEN}Fetched {_C.BOLD}{count}{_C.RESET}{_C.GREEN} items from {source}{_C.RESET}")

    @staticmethod
    def fetch_fail(source: str, error: str):
        PipelineLogger._print("fail", f"{_C.RED}Fetch failed for {source}{_C.RESET}", truncate(str(error), 100))

    # --- Parsing ---

    @staticmethod
    def parse_start(parser_name: str, title: str | None = None):
        msg = f"{_C.MAGENTA}Parsing{_C.RESET} with {_C.BOLD}{parser_name}{_C.RESET}"
        PipelineLogger._print("parse", msg, truncate(title, 60) if title else None)

    @staticmethod
    def parse_fail(title: str, error: str):
        PipelineLogger._print("fail", f"{_C.RED}Parse error{_C.RESET}  {truncate(title, 50)}", truncate(str(error), 80))

    # --- AI / LLM ---

    @staticmethod
    def ai_call(task: str, title: str | None = None):
        msg = f"{_C.YELLOW}LLM call:{_C.RESET} {_C.BOLD}{task}{_C.RESET}"
        PipelineLogger._print("ai", msg, truncate(title, 60) if title else None)

    @staticmethod
    def ai_result(task: str, output_preview: str | None = None):
        msg = f"{_C.GREEN}LLM done:{_C.RESET} {task}"
        PipelineLogger._print("ok", msg, truncate(output_preview, 80) if output_preview else None)

    @staticmethod
    def ai_classify(title: str, is_news: bool | None):
        label = {True: f"{_C.GREEN}✓ is news{_C.RESET}", False: f"{_C.RED}✗ not news{_C.RESET}", None: f"{_C.YELLOW}? ambiguous{_C.RESET}"}[is_news]
        PipelineLogger._print("ai", f"Classify → {label}", truncate(title, 60))

    # --- Saving ---

    @staticmethod
    def save(path: str, label: str = "Saved"):
        PipelineLogger._print("save", f"{_C.GREEN}{label}{_C.RESET}", truncate(path, 90))

    @staticmethod
    def save_skip(reason: str, detail: str | None = None):
        PipelineLogger._print("skip", f"{_C.GRAY}{reason}{_C.RESET}", truncate(detail, 80) if detail else None)

    # --- General ---

    @staticmethod
    def info(message: str, detail: str | None = None):
        PipelineLogger._print("info", message, detail)

    @staticmethod
    def warn(message: str, detail: str | None = None):
        PipelineLogger._print("warn", f"{_C.YELLOW}{message}{_C.RESET}", detail)

    @staticmethod
    def error(message: str, detail: str | None = None):
        PipelineLogger._print("fail", f"{_C.RED}{message}{_C.RESET}", detail)

    @staticmethod
    def success(message: str, detail: str | None = None):
        PipelineLogger._print("ok", f"{_C.GREEN}{message}{_C.RESET}", detail)

    # --- Chat / RAG ---

    @staticmethod
    def chat_query(user_id: str, query: str):
        PipelineLogger._print("chat", f"{_C.MAGENTA}Query{_C.RESET} from {_C.BOLD}{truncate(user_id, 16)}{_C.RESET}", truncate(query, 80))

    @staticmethod
    def rag_search(keywords: str, n_results: int):
        PipelineLogger._print("rag", f"{_C.CYAN}Search{_C.RESET} → {_C.BOLD}{n_results}{_C.RESET} results", truncate(keywords, 60))

    @staticmethod
    def chat_response(preview: str):
        PipelineLogger._print("chat", f"{_C.GREEN}Response ready{_C.RESET}", truncate(preview, 80))

    # --- DB ---

    @staticmethod
    def db(action: str, detail: str | None = None):
        PipelineLogger._print("db", f"{_C.GREEN}{action}{_C.RESET}", detail)

    # ── Section banners ─────────────────────────────────────────────────

    @staticmethod
    def section(title: str):
        """Print a prominent section banner."""
        bar = "─" * 60
        print(f"\n{_C.BOLD}{_C.CYAN}{bar}{_C.RESET}")
        print(f"{_C.BOLD}{_C.CYAN}  ▶  {title}{_C.RESET}")
        print(f"{_C.BOLD}{_C.CYAN}{bar}{_C.RESET}")

    @staticmethod
    def subsection(title: str):
        """Print a lighter sub-section header."""
        print(f"\n  {_C.BOLD}{_C.BLUE}── {title} ──{_C.RESET}")

    @staticmethod
    def divider():
        print(f"{_C.DIM}{'·' * 50}{_C.RESET}")

    # ── Timer context manager ───────────────────────────────────────────

    @staticmethod
    @contextmanager
    def timed(label: str):
        """Context manager that prints elapsed time on exit."""
        start = time.time()
        PipelineLogger._print("info", f"{_C.BLUE}Starting:{_C.RESET} {label}")
        try:
            yield
        finally:
            elapsed = time.time() - start
            if elapsed < 1:
                time_str = f"{elapsed * 1000:.0f}ms"
            elif elapsed < 60:
                time_str = f"{elapsed:.1f}s"
            else:
                mins, secs = divmod(elapsed, 60)
                time_str = f"{int(mins)}m {secs:.0f}s"
            PipelineLogger._print("ok", f"{_C.GREEN}Finished:{_C.RESET} {label}  {_C.DIM}({time_str}){_C.RESET}")


# Convenience alias
log = PipelineLogger
