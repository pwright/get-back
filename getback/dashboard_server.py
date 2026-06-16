"""Dashboard server for observability on port 9093."""

import asyncio
import logging
import json
import ssl
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .counter import Counter


logger = logging.getLogger(__name__)


def generate_openapi_spec(backend_host: str = 'localhost') -> dict:
    """Load OpenAPI 3.0 specification from YAML template and interpolate backend_host.

    Args:
        backend_host: Default backend host to interpolate into examples

    Returns:
        OpenAPI spec dict
    """
    import yaml
    from pathlib import Path

    spec_path = Path(__file__).parent / 'openapi-spec.yaml'
    with open(spec_path, 'r') as f:
        spec_yaml = f.read()

    # Interpolate backend_host placeholder
    spec_yaml = spec_yaml.replace('__BACKEND_HOST__', backend_host)

    return yaml.safe_load(spec_yaml)


def render_dashboard_html(backend_host: str = 'localhost') -> str:
    """Render dashboard HTML with backend host embedded.

    Args:
        backend_host: Default backend host for requests

    Returns:
        HTML string with embedded configuration
    """
    # Load template from file
    template_path = Path(__file__).parent / 'templates' / 'dashboard.html'

    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Substitute backend host placeholder
    return html.replace('__BACKEND_HOST__', backend_host)


def parse_backend(backend: str, default_host: str = 'localhost', default_port: int = 9091) -> tuple[str, int]:
    """Parse backend string in 'host:port' format.

    Args:
        backend: Backend string (e.g., 'getback:9091', 'localhost:9092')
        default_host: Default host if parsing fails
        default_port: Default port if parsing fails

    Returns:
        Tuple of (host, port)
    """
    if not backend or not backend.strip():
        return (default_host, default_port)

    try:
        if ':' in backend:
            host, port_str = backend.rsplit(':', 1)
            # Skip if port string is empty or whitespace
            if not port_str.strip():
                return (default_host, default_port)
            port = int(port_str.strip())
            if 1 <= port <= 65535 and host.strip():
                return (host.strip(), port)
    except (ValueError, AttributeError):
        pass

    return (default_host, default_port)


def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context for TLS connections.

    For testing/demo purposes, this creates a permissive context
    that doesn't verify certificates. In production, configure
    proper certificate validation.

    Returns:
        SSL context for TLS connections
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def compute_latency_percentile(latencies: list, percentile: float) -> int:
    """Compute percentile from latency list.

    Args:
        latencies: Sorted list of latency values
        percentile: Percentile to compute (0-100)

    Returns:
        Latency value at percentile (in ms)
    """
    if not latencies:
        return 0
    idx = int(len(latencies) * (percentile / 100))
    idx = min(idx, len(latencies) - 1)
    return latencies[idx]


def format_stats_json(
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    latency_stats: Dict[str, list],
    active_tcp_connections: set
) -> str:
    """Format stats as JSON with latency aggregates.

    Args:
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        latency_stats: Latency tracking dict ({"http": [...], "tcp": [...]})
        active_tcp_connections: Set of active persistent TCP connections

    Returns:
        JSON string with current stats and latency aggregates
    """
    # Compute HTTP latency stats
    http_latencies = sorted(latency_stats.get("http", []))
    http_latency = {}
    if http_latencies:
        http_latency = {
            "min": min(http_latencies),
            "max": max(http_latencies),
            "avg": int(sum(http_latencies) / len(http_latencies)),
            "p50": compute_latency_percentile(http_latencies, 50),
            "p95": compute_latency_percentile(http_latencies, 95),
            "p99": compute_latency_percentile(http_latencies, 99),
            "count": len(http_latencies)
        }

    # Compute TCP latency stats
    tcp_latencies = sorted(latency_stats.get("tcp", []))
    tcp_latency = {}
    if tcp_latencies:
        tcp_latency = {
            "min": min(tcp_latencies),
            "max": max(tcp_latencies),
            "avg": int(sum(tcp_latencies) / len(tcp_latencies)),
            "p50": compute_latency_percentile(tcp_latencies, 50),
            "p95": compute_latency_percentile(tcp_latencies, 95),
            "p99": compute_latency_percentile(tcp_latencies, 99),
            "count": len(tcp_latencies)
        }

    stats = {
        "http_counter": http_counter._value,
        "tcp_counter": tcp_counter._value,
        "active_tcp_connections": len(active_tcp_connections),
        "uptime": int(time.time() - start_time),
        "timestamp": int(time.time()),
        "latency": {
            "http": http_latency,
            "tcp": tcp_latency
        }
    }
    return json.dumps(stats)


async def make_http_request(backend_host: str = 'localhost', backend_port: int = 9091, use_tls: bool = False) -> Dict[str, Any]:
    """Make HTTP request to backend server.

    Args:
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9091)
        use_tls: Use HTTPS/TLS encryption (default: False)

    Returns:
        Dict with counter, server, latency_ms, timestamp
    """
    start = time.time()

    # Create SSL context if TLS enabled
    ssl_context = create_ssl_context() if use_tls else None

    reader, writer = await asyncio.open_connection(backend_host, backend_port, ssl=ssl_context)

    try:
        # Send HTTP request
        request = b"GET / HTTP/1.0\r\n\r\n"
        writer.write(request)
        await writer.drain()

        # Read response
        response = await reader.read(1024)
        response_text = response.decode('utf-8')

        # Parse response body (skip headers)
        body = response_text.split('\r\n\r\n', 1)[1].strip() if '\r\n\r\n' in response_text else ""

        # Parse JSON response
        if not body:
            raise ValueError("Empty response from backend")

        data = json.loads(body)
        counter = data["counter"]
        server = data["server"]
        backend_timestamp = data["timestamp"]  # Milliseconds from backend

        latency_ms = int((time.time() - start) * 1000)

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "timestamp": backend_timestamp
        }
    finally:
        writer.close()
        await writer.wait_closed()


async def make_tcp_request(
    command: str = "test",
    backend_host: str = 'localhost',
    backend_port: int = 9092,
    active_tcp_connections: set = None,
    use_tls: bool = False
) -> Dict[str, Any]:
    """Make TCP request to backend server.

    Args:
        command: TCP command to send
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9092)
        active_tcp_connections: Set to track persistent connections (optional)
        use_tls: Use TLS encryption (default: False)

    Returns:
        Dict with counter, server, latency_ms, command, timestamp
    """
    start = time.time()

    # Create SSL context if TLS enabled
    ssl_context = create_ssl_context() if use_tls else None

    reader, writer = await asyncio.open_connection(backend_host, backend_port, ssl=ssl_context)

    try:
        # Send TCP command
        writer.write(f"{command}\n".encode('utf-8'))
        await writer.drain()

        # Read response
        response = await reader.readline()
        response_text = response.decode('utf-8').strip()

        # Parse JSON response
        if not response_text:
            raise ValueError("Empty response from backend")

        data = json.loads(response_text)
        counter = data["counter"]
        server = data["server"]
        backend_timestamp = data["timestamp"]  # Milliseconds from backend

        latency_ms = int((time.time() - start) * 1000)

        # For OPEN command, keep connection alive
        if command == "OPEN" and active_tcp_connections is not None:
            active_tcp_connections.add(writer)
            logger.debug(f"Persistent connection opened to {backend_host}:{backend_port} (total: {len(active_tcp_connections)})")

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "command": command,
            "timestamp": backend_timestamp
        }
    finally:
        # Only close non-persistent connections
        if command != "OPEN":
            writer.close()
            await writer.wait_closed()


async def handle_http_request(
    request_body: str,
    backend_host: str,
    distribution_counts: Dict[str, int],
    latency_stats: Dict[str, list]
) -> bytes:
    """Handle /api/request/http POST requests."""
    req_backend = backend_host
    req_port = 9091
    amount = 1
    use_tls = False

    if request_body:
        try:
            body_json = json.loads(request_body)
            if 'backend' in body_json:
                req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9091)
            amount = body_json.get('amount', 1)
            use_tls = body_json.get('tls', False)
        except json.JSONDecodeError:
            pass

    # Make N concurrent requests to backend
    tasks = [make_http_request(req_backend, req_port, use_tls=use_tls) for _ in range(amount)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and track successful requests
    successful_results = []
    for result in results:
        if isinstance(result, dict):
            successful_results.append(result)
            # Track distribution server-side
            server = result.get('server', 'unknown')
            distribution_counts[server] = distribution_counts.get(server, 0) + 1
            # Track latency (keep last 1000)
            latency_stats["http"].append(result.get('latency_ms', 0))
            if len(latency_stats["http"]) > 1000:
                latency_stats["http"].pop(0)

    body = json.dumps({"results": successful_results, "total": amount, "successful": len(successful_results)})
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


async def handle_tcp_request(
    request_body: str,
    backend_host: str,
    distribution_counts: Dict[str, int],
    latency_stats: Dict[str, list],
    active_tcp_connections: set
) -> bytes:
    """Handle /api/request/tcp POST requests."""
    command = "test"
    req_backend = backend_host
    req_port = 9092
    amount = 1
    use_tls = False

    if request_body:
        try:
            body_json = json.loads(request_body)
            command = body_json.get("command", "test")
            if 'backend' in body_json:
                req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9092)
            amount = body_json.get('amount', 1)
            use_tls = body_json.get('tls', False)
        except json.JSONDecodeError:
            pass

    # Make N concurrent requests to backend
    tasks = [make_tcp_request(command, req_backend, req_port, active_tcp_connections, use_tls=use_tls) for _ in range(amount)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and track successful requests
    successful_results = []
    for result in results:
        if isinstance(result, dict):
            successful_results.append(result)
            # Track distribution server-side
            server = result.get('server', 'unknown')
            distribution_counts[server] = distribution_counts.get(server, 0) + 1
            # Track latency (keep last 1000)
            latency_stats["tcp"].append(result.get('latency_ms', 0))
            if len(latency_stats["tcp"]) > 1000:
                latency_stats["tcp"].pop(0)

    body = json.dumps({"results": successful_results, "total": amount, "successful": len(successful_results)})
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


def handle_stats(
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    latency_stats: Dict[str, list],
    active_tcp_connections: set
) -> bytes:
    """Handle /stats GET requests."""
    body = format_stats_json(http_counter, tcp_counter, start_time, latency_stats, active_tcp_connections)
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


def handle_distribution(distribution_counts: Dict[str, int]) -> bytes:
    """Handle /api/distribution GET requests."""
    total = sum(distribution_counts.values())
    dist = {
        server: {
            "count": count,
            "percent": round(count / total * 100, 1) if total > 0 else 0
        }
        for server, count in sorted(distribution_counts.items(), key=lambda x: x[1], reverse=True)
    }
    body = json.dumps({
        "distribution": dist,
        "total": total,
        "timestamp": int(time.time())
    })
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


def handle_distribution_reset(distribution_counts: Dict[str, int]) -> bytes:
    """Handle /api/distribution/reset POST requests."""
    old_total = sum(distribution_counts.values())
    distribution_counts.clear()
    body = json.dumps({
        "message": "Distribution reset",
        "cleared": old_total,
        "timestamp": int(time.time())
    })
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


async def handle_connections_close_all(
    active_tcp_connections: set,
    cycling_active: dict,
    current_cycle_task: dict
) -> bytes:
    """Handle /api/connections/close-all POST requests."""
    # Stop cycling if active
    was_cycling = cycling_active['active']
    cycling_active['active'] = False
    if current_cycle_task['task'] and not current_cycle_task['task'].done():
        current_cycle_task['task'].cancel()
        try:
            await current_cycle_task['task']
        except asyncio.CancelledError:
            pass

    # Close all persistent TCP connections
    count = len(active_tcp_connections)
    close_tasks = []
    for writer in list(active_tcp_connections):
        writer.close()
        close_tasks.append(writer.wait_closed())

    # Wait for all connections to close (with timeout)
    try:
        await asyncio.wait_for(
            asyncio.gather(*close_tasks, return_exceptions=True),
            timeout=2.0
        )
    except asyncio.TimeoutError:
        logger.warning(f"Timeout closing {count} connections")

    active_tcp_connections.clear()
    logger.info(f"Closed {count} persistent TCP connections{' and stopped cycling' if was_cycling else ''}")

    body = json.dumps({
        "message": "All connections closed" + (" and cycling stopped" if was_cycling else ""),
        "closed": count,
        "cycling_stopped": was_cycling,
        "timestamp": int(time.time())
    })
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


async def handle_connections_cycle(
    request_body: str,
    backend_host: str,
    active_tcp_connections: set,
    cycling_active: dict,
    current_cycle_task: dict
) -> bytes:
    """Handle /api/connections/cycle POST requests."""
    req_backend = backend_host
    req_port = 9092
    amount = 1
    use_tls = False

    if request_body:
        try:
            body_json = json.loads(request_body)
            backend_str = body_json.get('backend', f'{backend_host}:9092')
            req_backend, req_port = parse_backend(backend_str, backend_host, 9092)
            amount = body_json.get('amount', 1)
            amount = max(1, min(amount, 1000))  # Cap at 1000
            use_tls = body_json.get('tls', False)
        except (json.JSONDecodeError, ValueError):
            pass

    # Set cycling active flag
    cycling_active['active'] = True

    # Create SSL context if TLS enabled
    ssl_context = create_ssl_context() if use_tls else None

    # Start background task for continuous cycling
    async def cycle_connections_loop():
        ramp_duration = 20.0  # seconds
        interval = ramp_duration / amount if amount > 0 else 1.0
        cycle_count = 0

        try:
            logger.info(f"Cycle: starting continuous cycling with {amount} peak connections")

            while cycling_active['active']:
                cycle_count += 1
                opened_writers = []

                try:
                    # Ramp up: open connections gradually
                    logger.info(f"Cycle {cycle_count}: ramping up to {amount} connections")
                    for i in range(amount):
                        if not cycling_active['active']:
                            break

                        try:
                            reader, writer = await asyncio.open_connection(req_backend, req_port, ssl=ssl_context)
                            # Send OPEN command
                            writer.write(b"OPEN\n")
                            await writer.drain()
                            # Read response
                            await reader.readline()

                            active_tcp_connections.add(writer)
                            opened_writers.append(writer)

                            if i < amount - 1:  # Don't sleep after last one
                                await asyncio.sleep(interval)
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            logger.error(f"Cycle {cycle_count}: failed to open connection {i+1}: {e}")

                    if not cycling_active['active']:
                        break

                    logger.info(f"Cycle {cycle_count}: peak reached with {len(opened_writers)} connections")

                    # Ramp down: close connections gradually
                    logger.info(f"Cycle {cycle_count}: ramping down")
                    for i, writer in enumerate(opened_writers):
                        if not cycling_active['active']:
                            break

                        try:
                            writer.close()
                            await writer.wait_closed()
                            active_tcp_connections.discard(writer)

                            if i < len(opened_writers) - 1:  # Don't sleep after last one
                                await asyncio.sleep(interval)
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            logger.error(f"Cycle {cycle_count}: failed to close connection {i+1}: {e}")

                    logger.info(f"Cycle {cycle_count}: complete")

                except asyncio.CancelledError:
                    # Clean up connections on cancellation
                    for writer in opened_writers:
                        try:
                            writer.close()
                            await writer.wait_closed()
                            active_tcp_connections.discard(writer)
                        except Exception:
                            pass
                    raise

            logger.info(f"Cycling stopped after {cycle_count} cycles")

        except asyncio.CancelledError:
            logger.info(f"Cycling cancelled after {cycle_count} cycles")
        except Exception as e:
            logger.error(f"Cycle: error during cycling: {e}")
        finally:
            cycling_active['active'] = False

    # Fire and forget the cycle task
    current_cycle_task['task'] = asyncio.create_task(cycle_connections_loop())

    body = json.dumps({
        "message": "Continuous cycling started",
        "amount": amount,
        "cycle_duration": 40,
        "info": "Cycles will repeat until 'Close All' is pressed",
        "timestamp": int(time.time())
    })
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


def handle_openapi_spec(backend_host: str) -> bytes:
    """Handle /openapi.json GET requests."""
    spec = generate_openapi_spec(backend_host)
    body = json.dumps(spec, indent=2)
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "\r\n"
        f"{body}\n"
    ).encode('utf-8')


def handle_dashboard_html(backend_host: str) -> bytes:
    """Handle dashboard HTML GET requests (root or /dashboard)."""
    html = render_dashboard_html(backend_host)
    return (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "\r\n"
        f"{html}"
    ).encode('utf-8')


async def dashboard_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    backend_host: str,
    distribution_counts: Dict[str, int],
    latency_stats: Dict[str, list],
    active_tcp_connections: set,
    cycling_active: dict,
    current_cycle_task: dict
) -> None:
    """Handle dashboard HTTP requests.

    Args:
        reader: Async stream reader
        writer: Async stream writer
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests
        distribution_counts: Server-side distribution tracking dict
        latency_stats: Server-side latency tracking dict ({"http": [...], "tcp": [...]})
        active_tcp_connections: Set of active persistent TCP connections (dashboard → backends)
        cycling_active: Dict with 'active' key tracking if cycling is running
        current_cycle_task: Dict with 'task' key holding current cycle task
    """
    addr = writer.get_extra_info('peername')
    logger.debug(f"Dashboard request from {addr}")

    try:
        # Read HTTP request headers
        data = await reader.readuntil(b'\r\n\r\n')
        request_text = data.decode('utf-8')
        request_line = request_text.split('\r\n')[0]
        parts = request_line.split(' ')
        method = parts[0] if len(parts) >= 1 else "GET"
        path = parts[1] if len(parts) >= 2 else "/"
        logger.debug(f"Request: {method} {path}")

        # Parse Content-Length for POST requests
        content_length = 0
        for line in request_text.split('\r\n')[1:]:
            if line.lower().startswith('content-length:'):
                try:
                    content_length_str = line.split(':', 1)[1].strip()
                    if content_length_str:
                        content_length = int(content_length_str)
                except (ValueError, IndexError):
                    logger.warning(f"Invalid Content-Length header: {line}")
                break

        # Read request body if present
        request_body = ""
        if content_length > 0:
            body_data = await reader.readexactly(content_length)
            request_body = body_data.decode('utf-8')

        # Route to appropriate handler
        if path == "/api/request/http" and method == "POST":
            response = await handle_http_request(request_body, backend_host, distribution_counts, latency_stats)
        elif path == "/api/request/tcp" and method == "POST":
            response = await handle_tcp_request(request_body, backend_host, distribution_counts, latency_stats, active_tcp_connections)
        elif path == "/stats":
            response = handle_stats(http_counter, tcp_counter, start_time, latency_stats, active_tcp_connections)
        elif path == "/api/distribution":
            response = handle_distribution(distribution_counts)
        elif path == "/api/distribution/reset" and method == "POST":
            response = handle_distribution_reset(distribution_counts)
        elif path == "/api/connections/close-all" and method == "POST":
            response = await handle_connections_close_all(active_tcp_connections, cycling_active, current_cycle_task)
        elif path == "/api/connections/cycle" and method == "POST":
            response = await handle_connections_cycle(request_body, backend_host, active_tcp_connections, cycling_active, current_cycle_task)
        elif path == "/openapi.json":
            response = handle_openapi_spec(backend_host)
        else:
            response = handle_dashboard_html(backend_host)

        writer.write(response)
        await writer.drain()

    except asyncio.IncompleteReadError:
        logger.warning(f"Dashboard incomplete request from {addr}")
    except ValueError as e:
        # Likely a parsing error from backend response
        logger.error(f"Dashboard parsing error from {addr}: {e}")
        try:
            error_response = (
                "HTTP/1.0 502 Bad Gateway\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f'{{"error": "{str(e)}"}}\n'
            ).encode('utf-8')
            writer.write(error_response)
            await writer.drain()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Dashboard error from {addr}: {e}", exc_info=True)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_dashboard_server(
    host: str,
    port: int,
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    backend_host: str = 'localhost',
    ssl_context: Optional[ssl.SSLContext] = None
) -> None:
    """Start dashboard server.

    Args:
        host: Bind address
        port: Port number (typically 9093)
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests (default: localhost)
        ssl_context: Optional SSL context for TLS support
    """
    # Server-side distribution tracking
    distribution_counts = {}  # {"server_id": count}

    # Latency tracking (keep last 1000 requests per protocol)
    latency_stats = {
        "http": [],  # List of latency_ms values
        "tcp": []    # List of latency_ms values
    }

    # Track persistent TCP connections (dashboard → backends)
    active_tcp_connections = set()  # Set[asyncio.StreamWriter]

    # Track cycling state
    cycling_active = {'active': False}  # Use dict for mutability in closures
    current_cycle_task = {'task': None}  # Current background cycle task

    async def handler(reader, writer):
        await dashboard_handler(reader, writer, http_counter, tcp_counter, start_time, backend_host, distribution_counts, latency_stats, active_tcp_connections, cycling_active, current_cycle_task)

    server = await asyncio.start_server(handler, host, port, ssl=ssl_context)
    addr = server.sockets[0].getsockname()
    protocol = "https" if ssl_context else "http"
    logger.info(f"✓ Dashboard ready at {protocol}://{addr[0]}:{addr[1]}/")

    try:
        async with server:
            await server.serve_forever()
    finally:
        # Close all active persistent connections
        if active_tcp_connections:
            logger.info(f"Closing {len(active_tcp_connections)} active dashboard TCP connections...")
            close_tasks = []
            for writer in list(active_tcp_connections):
                writer.close()
                close_tasks.append(writer.wait_closed())
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning("Dashboard connection close timeout - forcing shutdown")
