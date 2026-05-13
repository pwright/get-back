"""Tests for HTTP server."""

import pytest
from getback.http_server import parse_http_request, format_http_response


def test_parse_http_request_root():
    """Should parse root path."""
    request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    assert parse_http_request(request) == "/"


def test_parse_http_request_health():
    """Should parse /health path."""
    request = b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n"
    assert parse_http_request(request) == "/health"


def test_parse_http_request_any_path():
    """Should parse arbitrary paths."""
    request = b"GET /api/counter HTTP/1.1\r\nHost: localhost\r\n\r\n"
    assert parse_http_request(request) == "/api/counter"


def test_parse_http_request_post():
    """Should parse POST requests."""
    request = b"POST /anything HTTP/1.1\r\nHost: localhost\r\n\r\n"
    assert parse_http_request(request) == "/anything"


def test_parse_http_request_malformed():
    """Malformed requests should default to /."""
    assert parse_http_request(b"garbage") == "/"
    assert parse_http_request(b"") == "/"


def test_format_http_response():
    """Should format HTTP/1.0 response correctly."""
    response = format_http_response("42")
    assert response == b"HTTP/1.0 200 OK\r\n\r\n42\n"


def test_format_http_response_health():
    """Should format health response."""
    response = format_http_response("OK")
    assert response == b"HTTP/1.0 200 OK\r\n\r\nOK\n"
