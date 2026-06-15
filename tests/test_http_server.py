"""Tests for HTTP server."""

import json
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


def test_format_http_response_json():
    """Should format HTTP/1.0 JSON response correctly."""
    body = '{"counter":42,"server":"test","timestamp":1234567890}'
    response = format_http_response(body, content_type="application/json")
    assert response.startswith(b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n")
    assert response.endswith(b"\n")

    # Verify JSON body
    response_body = response.split(b'\r\n\r\n', 1)[1].rstrip(b'\n')
    data = json.loads(response_body)
    assert data["counter"] == 42
    assert data["server"] == "test"
    assert data["timestamp"] == 1234567890


def test_format_http_response_text():
    """Should format HTTP/1.0 text response correctly."""
    response = format_http_response("OK", content_type="text/plain")
    assert response == b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nOK\n"
