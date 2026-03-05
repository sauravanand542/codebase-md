"""Tests for the CLI."""

from my_cli.utils import format_greeting


def test_format_greeting() -> None:
    assert format_greeting("Alice") == "Hello, Alice!"
