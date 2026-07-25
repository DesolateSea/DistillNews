from textual.screen import Screen
from textual.widgets import DataTable, Static, Header, Footer
from textual.containers import Grid, Vertical, ScrollableContainer
from textual.binding import Binding

from db import FileStore
import json


class ArticlesScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back", priority=True)
    ]

    def compose(self) -> None:
        yield Header(show_clock=True)
        with Grid(id="articles-screen"):
            yield DataTable(id="articles-table")
            with ScrollableContainer(id="article-detail"):
                yield Static("Select an article to view details", id="article-content")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Category", "Date", "Source", "ID")
        
        self.articles_data = {}
        
        files = FileStore.list_processed_files()
        for path in files:
            # article_id is the filename without extension
            article_id = path.stem
            try:
                article = FileStore.load_processed_article(article_id)
                if article:
                    self.articles_data[article_id] = article
                    table.add_row(
                        article.get("title", "Untitled"),
                        article.get("category", "Unknown"),
                        article.get("publication_date", ""),
                        article.get("source", ""),
                        article_id,
                        key=article_id
                    )
            except Exception:
                pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        article_id = event.row_key.value
        article = self.articles_data.get(article_id)
        
        content_widget = self.query_one("#article-content", Static)
        
        if article:
            # Format article details nicely
            content = f"[bold text-title]{article.get('title', 'Untitled')}[/]\n\n"
            content += f"[bold #58a6ff]Source:[/] {article.get('source', '')}\n"
            content += f"[bold #58a6ff]Category:[/] {article.get('category', '')}\n"
            content += f"[bold #58a6ff]Date:[/] {article.get('publication_date', '')}\n\n"
            content += f"[bold #3fb950]Content:[/]\n{article.get('content', 'No content')}\n"
            
            content_widget.update(content)
