"""Unit tests for utils.logger ANSI badge logger using pytest."""

from utils.logger import log, Logger, truncate


def test_truncate_helper():
    assert truncate("short text", max_len=20) == "short text"
    assert truncate("very long line that needs truncation", max_len=15) == "very long line…"
    assert truncate("line1\nline2", max_len=20) == "line1 line2"


def test_logger_badges_formatting(capsys):
    log.info("Test Info Message")
    captured = capsys.readouterr().out
    assert "[ INFO ]" in captured
    assert "Test Info Message" in captured

    log.warn("Test Warning Message")
    captured = capsys.readouterr().out
    assert "[ WARN ]" in captured
    assert "Test Warning Message" in captured

    log.error("Test Error Message")
    captured = capsys.readouterr().out
    assert "[ FAIL ]" in captured
    assert "Test Error Message" in captured

    log.success("Test Success Message")
    captured = capsys.readouterr().out
    assert "[  OK  ]" in captured
    assert "Test Success Message" in captured

    log.db("MongoDB Action", "connected")
    captured = capsys.readouterr().out
    assert "[  DB  ]" in captured
    assert "MongoDB Action" in captured
