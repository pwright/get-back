"""Tests for dashboard server."""

import pytest
import json
import asyncio
from getback.dashboard_server import (
    parse_backend,
    compute_latency_percentile,
    format_stats_json,
    generate_openapi_spec,
)
from getback.counter import Counter


# Test parse_backend function

def test_parse_backend_valid_format():
    """Should parse valid host:port format."""
    host, port = parse_backend("localhost:9091")
    assert host == "localhost"
    assert port == 9091


def test_parse_backend_hostname_with_port():
    """Should parse hostname with port."""
    host, port = parse_backend("getback:9091")
    assert host == "getback"
    assert port == 9091


def test_parse_backend_ip_with_port():
    """Should parse IP address with port."""
    host, port = parse_backend("192.168.1.100:8080")
    assert host == "192.168.1.100"
    assert port == 8080


def test_parse_backend_fqdn_with_port():
    """Should parse FQDN with port."""
    host, port = parse_backend("backend.example.com:9091")
    assert host == "backend.example.com"
    assert port == 9091


def test_parse_backend_empty_string():
    """Empty string should return defaults."""
    host, port = parse_backend("", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_no_port():
    """No port should return defaults."""
    host, port = parse_backend("hostname", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_empty_port():
    """Empty port should return defaults."""
    host, port = parse_backend("hostname:", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_invalid_port():
    """Invalid port should return defaults."""
    host, port = parse_backend("hostname:abc", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_port_out_of_range():
    """Port out of range should return defaults."""
    host, port = parse_backend("hostname:99999", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_negative_port():
    """Negative port should return defaults."""
    host, port = parse_backend("hostname:-100", "default-host", 8888)
    assert host == "default-host"
    assert port == 8888


def test_parse_backend_whitespace():
    """Should handle whitespace in host and port."""
    host, port = parse_backend(" hostname : 9091 ")
    assert host == "hostname"
    assert port == 9091


# Test compute_latency_percentile function

def test_compute_latency_percentile_empty_list():
    """Empty list should return 0."""
    assert compute_latency_percentile([], 50) == 0


def test_compute_latency_percentile_single_value():
    """Single value should return that value."""
    assert compute_latency_percentile([10], 50) == 10
    assert compute_latency_percentile([10], 95) == 10
    assert compute_latency_percentile([10], 99) == 10


def test_compute_latency_percentile_p50():
    """P50 should return median."""
    latencies = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert compute_latency_percentile(latencies, 50) == 5


def test_compute_latency_percentile_p95():
    """P95 should return 95th percentile."""
    latencies = list(range(1, 101))  # 1 to 100
    result = compute_latency_percentile(latencies, 95)
    assert 94 <= result <= 96  # Should be around 95


def test_compute_latency_percentile_p99():
    """P99 should return 99th percentile."""
    latencies = list(range(1, 101))  # 1 to 100
    result = compute_latency_percentile(latencies, 99)
    assert 98 <= result <= 100  # Should be around 99


def test_compute_latency_percentile_already_sorted():
    """Should work with already sorted list."""
    latencies = [1, 2, 3, 4, 5]
    assert compute_latency_percentile(latencies, 50) == 3


def test_compute_latency_percentile_bounds():
    """Should handle edge percentiles."""
    latencies = list(range(1, 11))
    assert compute_latency_percentile(latencies, 0) == 1
    assert compute_latency_percentile(latencies, 100) == 10


# Test format_stats_json function

@pytest.mark.asyncio
async def test_format_stats_json_basic():
    """Should format basic stats correctly."""
    http_counter = Counter()
    tcp_counter = Counter()
    await http_counter.increment()
    await http_counter.increment()
    await tcp_counter.increment()

    start_time = 1000.0
    latency_stats = {"http": [], "tcp": []}

    import time
    with pytest.MonkeyPatch.context() as m:
        m.setattr(time, "time", lambda: 1100.0)  # 100 seconds later

        result = format_stats_json(http_counter, tcp_counter, start_time, latency_stats)
        data = json.loads(result)

        assert data["http_counter"] == 2
        assert data["tcp_counter"] == 1
        assert data["uptime"] == 100
        assert "timestamp" in data
        assert "latency" in data


@pytest.mark.asyncio
async def test_format_stats_json_with_latency():
    """Should include latency stats when available."""
    http_counter = Counter()
    tcp_counter = Counter()

    start_time = 1000.0
    latency_stats = {
        "http": [5, 10, 15, 20, 25],
        "tcp": [3, 6, 9, 12]
    }

    import time
    with pytest.MonkeyPatch.context() as m:
        m.setattr(time, "time", lambda: 1100.0)

        result = format_stats_json(http_counter, tcp_counter, start_time, latency_stats)
        data = json.loads(result)

        assert "latency" in data
        assert "http" in data["latency"]
        assert "tcp" in data["latency"]

        # Check HTTP latency
        http_lat = data["latency"]["http"]
        assert http_lat["min"] == 5
        assert http_lat["max"] == 25
        assert http_lat["avg"] == 15
        assert http_lat["count"] == 5
        assert "p50" in http_lat
        assert "p95" in http_lat
        assert "p99" in http_lat

        # Check TCP latency
        tcp_lat = data["latency"]["tcp"]
        assert tcp_lat["min"] == 3
        assert tcp_lat["max"] == 12
        assert tcp_lat["count"] == 4


@pytest.mark.asyncio
async def test_format_stats_json_empty_latency():
    """Should handle empty latency stats."""
    http_counter = Counter()
    tcp_counter = Counter()

    start_time = 1000.0
    latency_stats = {"http": [], "tcp": []}

    import time
    with pytest.MonkeyPatch.context() as m:
        m.setattr(time, "time", lambda: 1100.0)

        result = format_stats_json(http_counter, tcp_counter, start_time, latency_stats)
        data = json.loads(result)

        # Latency should be empty dicts when no data
        assert data["latency"]["http"] == {}
        assert data["latency"]["tcp"] == {}


# Test generate_openapi_spec function

def test_generate_openapi_spec_structure():
    """Should generate valid OpenAPI 3.0 structure."""
    spec = generate_openapi_spec("localhost")

    assert spec["openapi"] == "3.0.0"
    assert "info" in spec
    assert "paths" in spec
    assert "components" in spec
    assert "servers" in spec


def test_generate_openapi_spec_info():
    """Should include API info."""
    spec = generate_openapi_spec("localhost")

    info = spec["info"]
    assert "title" in info
    assert "version" in info
    assert "description" in info
    assert "Get-Back" in info["title"]


def test_generate_openapi_spec_paths():
    """Should include all API paths."""
    spec = generate_openapi_spec("localhost")

    paths = spec["paths"]
    assert "/api/request/http" in paths
    assert "/api/request/tcp" in paths
    assert "/stats" in paths
    assert "/api/distribution" in paths
    assert "/api/distribution/reset" in paths


def test_generate_openapi_spec_http_endpoint():
    """Should define HTTP request endpoint correctly."""
    spec = generate_openapi_spec("localhost")

    endpoint = spec["paths"]["/api/request/http"]["post"]
    assert "summary" in endpoint
    assert "requestBody" in endpoint
    assert "responses" in endpoint

    # Check request body schema
    schema = endpoint["requestBody"]["content"]["application/json"]["schema"]
    assert "backend" in schema["properties"]
    assert "amount" in schema["properties"]
    assert schema["required"] == ["backend", "amount"]


def test_generate_openapi_spec_tcp_endpoint():
    """Should define TCP request endpoint correctly."""
    spec = generate_openapi_spec("localhost")

    endpoint = spec["paths"]["/api/request/tcp"]["post"]
    schema = endpoint["requestBody"]["content"]["application/json"]["schema"]

    assert "backend" in schema["properties"]
    assert "command" in schema["properties"]
    assert "amount" in schema["properties"]
    assert "backend" in schema["required"]
    assert "command" in schema["required"]
    assert "amount" in schema["required"]


def test_generate_openapi_spec_stats_endpoint():
    """Should define stats endpoint correctly."""
    spec = generate_openapi_spec("localhost")

    endpoint = spec["paths"]["/stats"]["get"]
    assert "summary" in endpoint
    assert "responses" in endpoint
    assert "200" in endpoint["responses"]


def test_generate_openapi_spec_components():
    """Should include schema components."""
    spec = generate_openapi_spec("localhost")

    schemas = spec["components"]["schemas"]
    assert "RequestResult" in schemas
    assert "TCPRequestResult" in schemas
    assert "Stats" in schemas
    assert "LatencyStats" in schemas
    assert "Distribution" in schemas
    assert "Error" in schemas


def test_generate_openapi_spec_latency_schema():
    """Should define latency stats schema."""
    spec = generate_openapi_spec("localhost")

    latency_schema = spec["components"]["schemas"]["LatencyStats"]
    props = latency_schema["properties"]

    assert "min" in props
    assert "max" in props
    assert "avg" in props
    assert "p50" in props
    assert "p95" in props
    assert "p99" in props
    assert "count" in props


def test_generate_openapi_spec_backend_host_interpolation():
    """Should use provided backend host in examples."""
    spec = generate_openapi_spec("custom-backend")

    http_endpoint = spec["paths"]["/api/request/http"]["post"]
    http_schema = http_endpoint["requestBody"]["content"]["application/json"]["schema"]

    # Should use custom backend in example
    assert "custom-backend" in http_schema["properties"]["backend"]["example"]


def test_generate_openapi_spec_tags():
    """Should include tags for organization."""
    spec = generate_openapi_spec("localhost")

    assert "tags" in spec
    tag_names = [tag["name"] for tag in spec["tags"]]
    assert "Requests" in tag_names
    assert "Metrics" in tag_names


def test_generate_openapi_spec_response_schemas():
    """Should define response schemas correctly."""
    spec = generate_openapi_spec("localhost")

    http_endpoint = spec["paths"]["/api/request/http"]["post"]
    responses = http_endpoint["responses"]

    # Check 200 response
    assert "200" in responses
    success_schema = responses["200"]["content"]["application/json"]["schema"]
    assert "results" in success_schema["properties"]
    assert "total" in success_schema["properties"]
    assert "successful" in success_schema["properties"]

    # Check error response
    assert "502" in responses


def test_generate_openapi_spec_valid_json():
    """Generated spec should be valid JSON."""
    spec = generate_openapi_spec("localhost")

    # Should be serializable to JSON
    json_str = json.dumps(spec)

    # Should be parseable back
    parsed = json.loads(json_str)
    assert parsed["openapi"] == "3.0.0"


# Integration-like tests for validation

def test_openapi_spec_amount_validation():
    """Amount parameter should have validation constraints."""
    spec = generate_openapi_spec("localhost")

    http_schema = spec["paths"]["/api/request/http"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    amount_prop = http_schema["properties"]["amount"]

    assert amount_prop["type"] == "integer"
    assert amount_prop["minimum"] == 1
    assert amount_prop["maximum"] == 10000


def test_latency_percentile_accuracy():
    """Percentile calculations should be accurate."""
    # Test with known distribution
    latencies = list(range(1, 1001))  # 1 to 1000

    p50 = compute_latency_percentile(latencies, 50)
    assert 495 <= p50 <= 505  # Should be around 500

    p95 = compute_latency_percentile(latencies, 95)
    assert 945 <= p95 <= 955  # Should be around 950

    p99 = compute_latency_percentile(latencies, 99)
    assert 985 <= p99 <= 995  # Should be around 990
