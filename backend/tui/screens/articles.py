from datetime import datetime, timezone
from pathlib import Path
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import DataTable, Static, Header, Footer
from textual.containers import Grid, Vertical, ScrollableContainer
from textual.binding import Binding
from rich.text import Text

from db import FileStore
import json


def _format_source(source_val) -> str:
    if isinstance(source_val, dict):
        sub = source_val.get("subreddit")
        if sub:
            return f"Reddit (r/{sub})"
        title = source_val.get("title") or source_val.get("name")
        if title:
            return str(title)
        return str(source_val)
    return str(source_val or "")


def _get_creation_time(article: dict, path: Path) -> str:
    if "created_at" in article and article["created_at"]:
        return str(article["created_at"])
    if "publication_date" in article and article["publication_date"]:
        return str(article["publication_date"])
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return ""


class ArticlesScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", priority=True)
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="articles-screen"):
            yield DataTable(id="articles-table")
            with ScrollableContainer(id="article-detail"):
                yield Static("Select an article to view details", id="article-content")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Title", "Category", "Pub Date", "Created At", "Source", "ID")
        
        self.articles_data = {}
        items = []
        
        files = FileStore.list_processed_files()
        for path in files:
            article_id = path.stem
            try:
                article = FileStore.load_processed_article(article_id)
                if article:
                    self.articles_data[article_id] = article
                    created_at = _get_creation_time(article, path)
                    items.append((created_at, article_id, article))
            except Exception:
                pass

        # Sort latest created_at first
        items.sort(key=lambda x: x[0], reverse=True)

        for created_at, article_id, article in items:
            display_created = created_at[:19].replace("T", " ") if created_at else ""
            table.add_row(
                article.get("title", "Untitled"),
                article.get("category", "Unknown"),
                article.get("publication_date", ""),
                display_created,
                _format_source(article.get("source")),
                article_id,
                key=article_id
            )

    def _show_article_detail(self, article_id: str) -> None:
        article = self.articles_data.get(article_id)
        content_widget = self.query_one("#article-content", Static)
        
        if article:
            title = str(article.get('title', 'Untitled'))
            source = _format_source(article.get('source'))
            category = str(article.get('category', 'Unknown'))
            pub_date = str(article.get('publication_date', ''))
            created_at = str(article.get('created_at', ''))
            body = str(article.get('content') or article.get('summary') or 'No content')
            
            t = Text()
            t.append(title, style="bold #ffffff")
            t.append("\n\n")
            t.append("Source: ", style="bold #58a6ff")
            t.append(source + "\n", style="#c9d1d9")
            t.append("Category: ", style="bold #58a6ff")
            t.append(category + "\n", style="#c9d1d9")
            t.append("Publication Date: ", style="bold #58a6ff")
            t.append(pub_date + "\n", style="#c9d1d9")
            if created_at:
                t.append("Created At: ", style="bold #58a6ff")
                t.append(created_at + "\n", style="#c9d1d9")
            t.append("\nContent:\n", style="bold #3fb950")
            t.append(body + "\n", style="#c9d1d9")
            
            content_widget.update(t)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value:
            self._show_article_detail(event.row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value:
            self._show_article_detail(event.row_key.value)


