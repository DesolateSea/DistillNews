from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import DataTable, Static, Header, Footer
from textual.containers import Grid, Vertical, ScrollableContainer
from textual.binding import Binding
from textual import work
from rich.text import Text

from service.db import create_article_store
from config import config
import json


def _format_source(source_val) -> str:
    if not source_val:
        return "—"
    if isinstance(source_val, dict):
        sub = source_val.get("subreddit")
        if sub:
            return f"r/{sub}"
        name = source_val.get("name") or source_val.get("source_name")
        if name and isinstance(name, str) and not name.startswith("http"):
            return name
        url = source_val.get("url") or source_val.get("link")
        if url and isinstance(url, str):
            try:
                domain = urlparse(url).netloc.replace("www.", "")
                if domain:
                    return domain
            except Exception:
                pass
        return "Web Source"
    elif isinstance(source_val, str):
        if source_val.startswith("http"):
            try:
                domain = urlparse(source_val).netloc.replace("www.", "")
                if domain:
                    return domain
            except Exception:
                pass
        return source_val
    return str(source_val)


class ArticlesScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", priority=True)
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="articles-screen"):
            yield DataTable(id="articles-table")
            with ScrollableContainer(id="article-detail"):
                yield Static("Loading articles...", id="article-content")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_column("Title", key="title")
        table.add_column("Category", key="category", width=15)
        table.add_column("Pub Date", key="date", width=12)
        table.add_column("ID", key="id", width=12)

        self.articles_data = {}
        self._load_articles_async()

    @work(thread=True)
    def _load_articles_async(self) -> None:
        try:
            article_store = create_article_store()
            all_articles = article_store.list_articles()
            all_articles.sort(key=lambda x: str(x.get("publication_date") or x.get("created_at") or ""), reverse=True)
            self.app.call_from_thread(self._populate_table, all_articles)
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _show_error(self, err_msg: str) -> None:
        content_widget = self.query_one("#article-content", Static)
        content_widget.update(f"[red]Error loading articles: {err_msg}[/red]")

    def _populate_table(self, all_articles: list) -> None:
        table = self.query_one(DataTable)
        table.clear()

        content_widget = self.query_one("#article-content", Static)
        if not all_articles:
            content_widget.update("No articles found in active store.")
            return

        content_widget.update("Select an article to view details")

        # Dynamically compute title column width from container size
        total_w = table.size.width or 95
        cat_w = 15
        date_w = 12
        id_w = 12
        fixed_sum = cat_w + date_w + id_w + 10
        title_w = max(20, total_w - fixed_sum)

        if "title" in table.columns:
            table.columns["title"].width = title_w

        for article in all_articles:
            article_id = article.get("id", "")
            if not article_id:
                continue
            self.articles_data[article_id] = article

            raw_title = str(article.get("title", "Untitled") or "Untitled").strip()
            title = (raw_title[:title_w - 2] + "…") if len(raw_title) > title_w else raw_title

            cat = str(article.get("category", "Unknown") or "Unknown").strip()
            category = (cat[:cat_w - 2] + "…") if len(cat) > cat_w else cat

            pub_date = str(article.get("publication_date", ""))[:10] or "—"

            short_id = article_id[:10]

            table.add_row(
                title,
                category,
                pub_date,
                short_id,
                key=article_id
            )

    def _show_article_detail(self, article_id: str) -> None:
        self._fetch_and_render_detail_async(article_id)

    @work(thread=True)
    def _fetch_and_render_detail_async(self, article_id: str) -> None:
        article = self.articles_data.get(article_id)
        if article and "content" not in article and "summary" not in article:
            try:
                article_store = create_article_store()
                full_art = article_store.load_article(article_id)
                if full_art:
                    article = full_art
                    self.articles_data[article_id] = article
            except Exception:
                pass

        self.app.call_from_thread(self._render_detail, article_id, article)

    def _render_detail(self, article_id: str, article: dict | None) -> None:
        content_widget = self.query_one("#article-content", Static)

        if article:
            title = str(article.get('title', 'Untitled'))
            source = _format_source(article.get('source'))
            category = str(article.get('category', 'Unknown'))
            pub_date = str(article.get('publication_date', ''))
            created_at = str(article.get('created_at', ''))
            body = str(article.get('content') or article.get('summary') or article.get('markdown_content') or 'No content')

            store_backend = config.ARTICLE_STORE_BACKEND
            store_label = "Azure Blob Storage" if store_backend == "azure" else "Local Disk (FileStore)"

            t = Text()
            t.append(title, style="bold #ffffff")
            t.append("\n\n")
            t.append("Active Store Backend: ", style="bold #e3b341")
            t.append(f"{store_label} [{store_backend}]\n", style="#c9d1d9")
            t.append("Source: ", style="bold #58a6ff")
            t.append(source + "\n", style="#c9d1d9")
            t.append("Category: ", style="bold #58a6ff")
            t.append(category + "\n", style="#c9d1d9")
            t.append("Publication Date: ", style="bold #58a6ff")
            t.append(pub_date + "\n", style="#c9d1d9")
            if created_at:
                t.append("Created At: ", style="bold #58a6ff")
                t.append(created_at + "\n", style="#c9d1d9")
            t.append("Article ID: ", style="bold #58a6ff")
            t.append(article_id + "\n", style="#c9d1d9")
            t.append("\nContent:\n", style="bold #3fb950")
            t.append(body + "\n", style="#c9d1d9")

            content_widget.update(t)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value:
            self._show_article_detail(event.row_key.value)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key.value:
            self._show_article_detail(event.row_key.value)
