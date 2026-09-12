"""
Tests for Textual TUI task manager dashboard (pipeline/tui/app.py).
"""

import pytest
from pipeline.tui.app import DistillNewsApp, TaskRow, STAGE_DEFS
from pipeline.runner import LogEvent
from pipeline.engine.task import TaskEvent, TaskState
from textual.widgets import RichLog, Button, ProgressBar, Static


@pytest.mark.asyncio
async def test_tui_app_mount_and_widgets():
    """Verify that DistillNewsApp mounts and renders task manager controls."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        assert pilot.app.title == "DistillNews"

        # Check interchangeable run/stop button
        btn_run_stop = pilot.app.query_one("#btn-run-stop", Button)
        assert btn_run_stop is not None
        assert "RUN" in str(btn_run_stop.label)

        # Check config buttons
        assert pilot.app.query_one("#btn-toggle-store", Button) is not None
        assert pilot.app.query_one("#btn-stage-fetch", Button) is not None
        assert pilot.app.query_one("#btn-stage-scrape", Button) is not None
        assert pilot.app.query_one("#btn-articles", Button) is not None

        # Check all task rows exist
        for stage_id, _, _ in STAGE_DEFS:
            row = pilot.app.query_one(f"#row-{stage_id}", TaskRow)
            assert row is not None
            assert pilot.app.query_one(f"#lbl-{stage_id}", Static) is not None

        # Check log panel
        log_widget = pilot.app.query_one("#main-log", RichLog)
        assert log_widget is not None


@pytest.mark.asyncio
async def test_tui_button_run_stop_toggle():
    """Verify interchangeable RUN PIPELINE / STOP button state."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        btn = pilot.app.query_one("#btn-run-stop", Button)
        assert "RUN" in str(btn.label)

        # Simulate setting running state
        pilot.app._set_running_state()
        assert "STOP" in str(btn.label)
        assert btn.variant == "error"
        assert pilot.app._is_running is True

        # Simulate setting idle state
        pilot.app._set_idle_state()
        assert "RUN" in str(btn.label)
        assert btn.variant == "primary"
        assert pilot.app._is_running is False


@pytest.mark.asyncio
async def test_tui_task_event_handling():
    """Verify that TaskEvents update task rows with WAITING, RUNNING, and DONE states."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        row_parse = pilot.app.query_one("#row-parse", TaskRow)
        lbl_parse = pilot.app.query_one("#lbl-parse", Static)

        # 1. Waiting event
        event_waiting = TaskEvent(
            task_id="t1",
            stage_name="parse",
            article_id="art1",
            state=TaskState.WAITING,
        )
        pilot.app._handle_event(event_waiting)
        assert "WAITING FOR sources" in str(lbl_parse._render())

        # 2. Running event
        event_running = TaskEvent(
            task_id="t1",
            stage_name="parse",
            article_id="art1",
            state=TaskState.RUNNING,
        )
        pilot.app._handle_event(event_running)
        assert "RUNNING" in str(lbl_parse._render())

        # 3. Done event
        event_done = TaskEvent(
            task_id="t1",
            stage_name="parse",
            article_id="art1",
            state=TaskState.DONE,
        )
        pilot.app._handle_event(event_done)
        assert "Done (1)" in str(lbl_parse._render())

        # 4. Log event
        pilot.app._handle_event(LogEvent(badge="info", message="Test message"))


@pytest.mark.asyncio
async def test_tui_task_row_text_formatting():
    """Verify TaskRow displays aligned text with items parsed, elapsed time, and status."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        row = pilot.app.query_one("#row-parse", TaskRow)
        lbl = pilot.app.query_one("#lbl-parse", Static)

        # Initially idle: shows 0 items parsed, 0.0s elapsed, Idle
        rendered = str(lbl._render())
        assert "0 items parsed" in rendered
        assert "0.0s elapsed" in rendered
        assert "Idle" in rendered

        # Waiting: shows WAITING FOR sources
        row.set_waiting("sources")
        rendered = str(lbl._render())
        assert "WAITING FOR sources" in rendered

        # Running: shows items parsed, elapsed, RUNNING
        row.set_running(current=5, total=10)
        rendered = str(lbl._render())
        assert "5 items parsed" in rendered
        assert "RUNNING" in rendered
        assert "elapsed" in rendered

        # Done: shows Done
        row.set_done(count=5)
        rendered = str(lbl._render())
        assert "5 items parsed" in rendered
        assert "Done" in rendered


@pytest.mark.asyncio
async def test_tui_task_row_disabled_state():
    """Verify disabled TaskRow displays '-' for items and elapsed, 'Disabled' for status, and rejects set_done."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        row = pilot.app.query_one("#row-parse", TaskRow)
        lbl = pilot.app.query_one("#lbl-parse", Static)

        # Set disabled
        row.set_disabled()
        rendered = str(lbl._render())
        assert "Disabled" in rendered
        assert "parse" in rendered
        # Should not display "0 items parsed" or "0.0s elapsed"
        assert "items parsed" not in rendered
        assert "elapsed" not in rendered
        assert "-" in rendered

        # Subsequent calls to set_done, set_running, set_waiting should be ignored
        row.set_done(count=10)
        rendered = str(lbl._render())
        assert "Disabled" in rendered
        assert "Done" not in rendered

        row.set_running(current=2)
        rendered = str(lbl._render())
        assert "Disabled" in rendered
        assert "RUNNING" not in rendered


@pytest.mark.asyncio
async def test_tui_task_row_descriptions():
    """Verify TaskRow displays a short description taken from the first line of its docstring."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        for stage_id, _, _ in STAGE_DEFS:
            row = pilot.app.query_one(f"#row-{stage_id}", TaskRow)
            lbl = pilot.app.query_one(f"#lbl-{stage_id}", Static)
            rendered = str(lbl._render())

            # Description should be non-empty and present in rendered output
            assert row.description != ""
            assert row.description in rendered

        # Spot check specific docstring descriptions
        row_parse = pilot.app.query_one("#row-parse", TaskRow)
        assert row_parse.description == "Parse a raw article item into a standardized dict."

        row_gnews = pilot.app.query_one("#row-fetch_gnews", TaskRow)
        assert row_gnews.description == "Fetch articles from GNews API."

        row_scrape = pilot.app.query_one("#row-scrape_targets", TaskRow)
        assert row_scrape.description == "Yield target URLs for web scraping."




@pytest.mark.asyncio
async def test_tui_toggle_logs_focus():
    """Verify action_toggle_logs switches focus between log panel and main task panel."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        panel = pilot.app.query_one("#main-panel")
        log = pilot.app.query_one("#main-log")

        # By default, main panel is focused on mount
        assert panel.has_focus

        # Toggle logs -> focus moves to log
        pilot.app.action_toggle_logs()
        await pilot.pause()
        assert log.has_focus

        # Toggle logs again -> focus returns to main panel
        pilot.app.action_toggle_logs()
        await pilot.pause()
        assert panel.has_focus


@pytest.mark.asyncio
async def test_tui_footer_bindings_clean():
    """Verify footer bindings descriptions do not contain redundant (key) parentheticals."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        descriptions = [b.description for b in pilot.app.BINDINGS]
        assert "View Logs" in descriptions
        assert "Run/Stop" in descriptions
        assert "Stop Tasks" in descriptions
        assert "Articles" in descriptions
        assert "Quit" in descriptions

        for desc in descriptions:
            assert "(b)" not in desc
            assert "(p)" not in desc
            assert "(x)" not in desc
            assert "(a)" not in desc


@pytest.mark.asyncio
async def test_tui_main_panel_scrolling():
    """Verify that the Tasks region (#main-panel) can be focused and scrolled."""
    app = DistillNewsApp()
    async with app.run_test(size=(80, 15)) as pilot:
        panel = pilot.app.query_one("#main-panel")
        assert panel.can_focus
        assert panel.has_focus
        assert panel.max_scroll_y > 0

        initial_y = panel.scroll_y
        await pilot.press("down")
        await pilot.pause()
        assert panel.scroll_y > initial_y


@pytest.mark.asyncio
async def test_tui_source_buttons_clean_names():
    """Verify source toggle buttons display only the source name without ENABLED/DISABLED text."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        for name in ["core", "gnews", "reddit", "media_stack", "news_org", "rapid_news"]:
            btn = pilot.app.query_one(f"#btn-src-{name}", Button)
            label_str = str(btn.label)
            assert label_str == name
            assert "ENABLED" not in label_str
            assert "DISABLED" not in label_str

        # Clicking toggles variant while keeping label as source name
        btn_core = pilot.app.query_one("#btn-src-core", Button)
        initial_variant = btn_core.variant
        btn_core.press()
        await pilot.pause()
        assert str(btn_core.label) == "core"
        assert btn_core.variant != initial_variant


@pytest.mark.asyncio
async def test_tui_stage_fetch_toggle():
    """Verify Stages section Fetch button toggles stage fetch and disables fetch tasks on run."""
    from config import config
    config.set_stage_enabled("fetch", True)
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        btn_fetch = pilot.app.query_one("#btn-stage-fetch", Button)
        assert str(btn_fetch.label) == "Fetch"
        assert btn_fetch.variant == "success"

        # Press to toggle fetch off
        btn_fetch.press()
        await pilot.pause()
        assert btn_fetch.variant == "default"
        assert config.is_stage_enabled("fetch") is False

        # Run pipeline with fetch disabled -> all fetch_* tasks marked disabled
        pilot.app.action_toggle_run()
        for s_id in ["fetch_reddit", "fetch_gnews", "fetch_core"]:
            row = pilot.app.query_one(f"#row-{s_id}", TaskRow)
            lbl = pilot.app.query_one(f"#lbl-{s_id}", Static)
            assert "Disabled" in str(lbl._render())

        # Cleanup
        pilot.app.action_stop()
        config.set_stage_enabled("fetch", True)


@pytest.mark.asyncio
async def test_tui_stage_scrape_toggle():
    """Verify Stages section Scrape button toggles stage scrape and disables scrape_targets on run."""
    from config import config
    config.set_stage_enabled("scrape", True)
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        btn_scrape = pilot.app.query_one("#btn-stage-scrape", Button)
        assert str(btn_scrape.label) == "Scrape"
        assert btn_scrape.variant == "success"

        # Press to toggle scrape off
        btn_scrape.press()
        await pilot.pause()
        assert btn_scrape.variant == "default"
        assert config.is_stage_enabled("scrape") is False

        # Run pipeline with scrape disabled -> scrape_targets task marked disabled
        pilot.app.action_toggle_run()
        row = pilot.app.query_one("#row-scrape_targets", TaskRow)
        lbl = pilot.app.query_one("#lbl-scrape_targets", Static)
        assert "Disabled" in str(lbl._render())

        # Cleanup
        pilot.app.action_stop()
        config.set_stage_enabled("scrape", True)


@pytest.mark.asyncio
async def test_tui_task_waiting_no_garbled_hash():
    """Verify that task waiting states never display garbled hex hashes."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        row_dedup = pilot.app.query_one("#row-dedup", TaskRow)
        lbl_dedup = pilot.app.query_one("#lbl-dedup", Static)

        # Emit an event with a raw hex task ID hash in waiting_on
        event = TaskEvent(
            task_id="t1",
            stage_name="dedup",
            article_id="art1",
            state=TaskState.WAITING,
            waiting_on=["f54b3ce86472"],
        )
        pilot.app._handle_event(event)
        rendered = str(lbl_dedup._render())

        # Must display clean upstream name 'parse', NOT the hex hash 'f54b3ce86472'
        assert "f54b3ce86472" not in rendered
        assert "parse" in rendered


@pytest.mark.asyncio
async def test_tui_action_stop_cancels_all_tasks_promptly():
    """Verify action_stop immediately marks active and waiting tasks as Stopped."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        row_parse = pilot.app.query_one("#row-parse", TaskRow)
        row_dedup = pilot.app.query_one("#row-dedup", TaskRow)

        row_parse.set_running(current=1)
        row_dedup.set_waiting("parse")

        pilot.app._is_running = True
        pilot.app.action_stop()

        lbl_parse = pilot.app.query_one("#lbl-parse", Static)
        lbl_dedup = pilot.app.query_one("#lbl-dedup", Static)

        assert "Stopped" in str(lbl_parse._render())
        assert "Stopped" in str(lbl_dedup._render())
        assert pilot.app._is_running is False


@pytest.mark.asyncio
async def test_tui_log_formatting_markup():
    """Verify that log messages with rich markup tags are formatted, not escaped."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        pilot.app._handle_log("INFO", "Source 'core' is now [green]ENABLED[/green]")
        pilot.app._handle_log("INFO", "Store set to [bold]Azure[/bold]")

        log_widget = pilot.app.query_one("#main-log", RichLog)
        text = "\n".join(str(line.text) for line in log_widget.lines)
        # Should contain formatted text, not escaped raw literal tags
        assert "ENABLED" in text
        assert "Azure" in text
        assert "[green]" not in text
        assert "[/green]" not in text
        assert "[bold]" not in text
        assert "[/bold]" not in text


@pytest.mark.asyncio
async def test_tui_article_count_in_sidebar_above_browse_articles():
    """Verify article count is positioned in sidebar right above Browse Articles button."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        sidebar = pilot.app.query_one("#sidebar")
        count_widget = pilot.app.query_one("#article-count", Static)
        btn_articles = pilot.app.query_one("#btn-articles", Button)

        # Both must be inside sidebar
        assert count_widget in sidebar.children
        assert btn_articles in sidebar.children

        # article-count must be directly above btn-articles
        count_idx = sidebar.children.index(count_widget)
        btn_idx = sidebar.children.index(btn_articles)
        assert count_idx == btn_idx - 1


@pytest.mark.asyncio
async def test_tui_log_shows_article_name_in_detail():
    """Verify log output displays article title and ID in detail line."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        log_event = LogEvent(
            badge="done",
            message="extract complete",
            detail='"Deep Learning Breakthrough in Medicine" (13906d9d)',
        )
        pilot.app._handle_event(log_event)

        log_widget = pilot.app.query_one("#main-log", RichLog)
        text = "\n".join(str(line.text) for line in log_widget.lines)
        assert "extract complete" in text
        assert "Deep Learning Breakthrough in Medicine" in text
        assert "13906d9d" in text


@pytest.mark.asyncio
async def test_tui_panel_titles_red():
    """Verify Pipeline Control and Pipeline Task Manager titles have red styling."""
    app = DistillNewsApp()
    async with app.run_test() as pilot:
        lbl_control = pilot.app.query_one("#lbl-pipeline-control", Static)
        lbl_manager = pilot.app.query_one("#lbl-task-manager", Static)

        assert "Pipeline Control" in str(lbl_control._render())
        assert "Pipeline Task Manager" in str(lbl_manager._render())

        assert "panel-title-red" in lbl_control.classes
        assert "panel-title-red" in lbl_manager.classes


