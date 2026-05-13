"""Tests for TCP server."""

import pytest
from getback.tcp_server import parse_tcp_command


def test_parse_tcp_command_numeric():
    """Numeric commands should return timed mode."""
    assert parse_tcp_command("5") == ("timed", 5)
    assert parse_tcp_command("10") == ("timed", 10)
    assert parse_tcp_command("1") == ("timed", 1)


def test_parse_tcp_command_open():
    """OPEN command should return persistent mode."""
    assert parse_tcp_command("OPEN") == ("persistent", None)
    assert parse_tcp_command("open") == ("persistent", None)
    assert parse_tcp_command("Open") == ("persistent", None)


def test_parse_tcp_command_immediate():
    """Non-numeric commands should return immediate mode."""
    assert parse_tcp_command("test") == ("immediate", 0)
    assert parse_tcp_command("hello") == ("immediate", 0)
    assert parse_tcp_command("") == ("immediate", 0)


def test_parse_tcp_command_invalid_numbers():
    """Invalid numbers should be treated as immediate."""
    assert parse_tcp_command("5.5") == ("immediate", 0)
    assert parse_tcp_command("-10") == ("immediate", 0)
    assert parse_tcp_command("abc123") == ("immediate", 0)


def test_parse_tcp_command_zero():
    """Zero should be treated as immediate (not timed)."""
    assert parse_tcp_command("0") == ("immediate", 0)
