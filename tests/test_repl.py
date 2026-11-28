"""Tests for the interactive `trawl repl` command (issue #48)."""

import os
import subprocess
import sys


def _run_repl(stdin_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "trawl", "repl"],
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def test_repl_prints_output_and_stack_per_line():
    res = _run_repl("1 2 + .\n")
    assert res.returncode == 0
    assert "trawl[0]> 3   []" in res.stdout


def test_repl_remembers_defined_words_across_lines():
    res = _run_repl(": sq dup * ;\n5 sq .\n")
    assert res.returncode == 0
    assert "trawl[0]> []" in res.stdout
    assert "trawl[1]> 25   []" in res.stdout


def test_repl_carries_stack_across_lines():
    res = _run_repl("3\n4 + .\n")
    assert res.returncode == 0
    assert "trawl[0]> [3]" in res.stdout
    assert "trawl[1]> 7   []" in res.stdout


def test_repl_error_does_not_exit_and_restores_stack():
    res = _run_repl("5\ndrop drop\n.\n")
    assert res.returncode == 0
    assert "(stack put back: [5])" in res.stdout
    assert "trawl[2]> 5   []" in res.stdout


def test_repl_catches_infinite_loop_and_continues():
    res = _run_repl("1 [ ]\n42 .\n")
    assert res.returncode == 0
    assert "the tide is stuck" in res.stdout
    assert "trawl[1]> 42   []" in res.stdout


def test_repl_welcome_example_works():
    res = _run_repl("use stdlib 10 fib .\n")
    assert res.returncode == 0
    assert "trawl[0]> 55   []" in res.stdout


def test_repl_eof_exits_cleanly():
    res = _run_repl("")
    assert res.returncode == 0
    assert "the tide goes out. bye." in res.stdout
