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


def test_parse_tcp_command_half_close_send():
    """HALF_CLOSE_SEND command should return half_close_send mode."""
    assert parse_tcp_command("HALF_CLOSE_SEND") == ("half_close_send", None)
    assert parse_tcp_command("half_close_send") == ("half_close_send", None)
    assert parse_tcp_command("Half_Close_Send") == ("half_close_send", None)


def test_parse_tcp_command_half_close_read():
    """HALF_CLOSE_READ command should return half_close_read mode."""
    assert parse_tcp_command("HALF_CLOSE_READ") == ("half_close_read", None)
    assert parse_tcp_command("half_close_read") == ("half_close_read", None)
    assert parse_tcp_command("Half_Close_Read") == ("half_close_read", None)
