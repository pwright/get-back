"""Dashboard server for observability on port 9093."""

import asyncio
import logging
import json
import time
from typing import Dict, Any
from .counter import Counter


logger = logging.getLogger(__name__)


def render_dashboard_html(backend_host: str = 'localhost') -> str:
    """Render dashboard HTML with backend host embedded.

    Args:
        backend_host: Default backend host for requests

    Returns:
        HTML string with embedded configuration
    """
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Get-Back Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #888; margin-bottom: 30px; font-size: 1.1rem; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        }
        .metric-label {
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric.http .metric-value {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric.tcp .metric-value {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-delta {
            color: #4caf50;
            font-size: 0.9rem;
            margin-top: 8px;
        }
        .status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            background: #2e7d32;
            color: white;
        }
        .footer {
            text-align: center;
            color: #666;
            margin-top: 40px;
            font-size: 0.9rem;
        }
        .config {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .config h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .config-row {
            display: grid;
            grid-template-columns: 120px 1fr auto;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
        }
        .config-row label {
            color: #888;
            font-size: 0.9rem;
        }
        .config-row input {
            background: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            padding: 8px 12px;
            color: #e0e0e0;
            font-family: monospace;
            font-size: 0.9rem;
        }
        .config-row input:focus {
            outline: none;
            border-color: #667eea;
        }
        .config-row button {
            padding: 8px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .config-row button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .controls {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .controls h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .button-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .button-group label {
            color: #888;
            font-size: 0.9rem;
            width: 100%;
            margin-bottom: 4px;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        button.http {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        button.tcp {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }
        button.tcp.secondary {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        }
        .history {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            max-height: 400px;
            overflow-y: auto;
        }
        .history h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .history-entry {
            background: #1a1a1a;
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 8px;
            font-size: 0.85rem;
            display: grid;
            grid-template-columns: auto 1fr auto;
            gap: 12px;
            align-items: center;
        }
        .history-entry .time {
            color: #666;
            font-family: monospace;
        }
        .history-entry .protocol {
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
        }
        .history-entry .protocol.http {
            background: #f5576c;
            color: white;
        }
        .history-entry .protocol.tcp {
            background: #00f2fe;
            color: #1a1a1a;
        }
        .history-entry .details {
            color: #e0e0e0;
        }
        .history-entry .server {
            color: #667eea;
            font-weight: 600;
        }
        .history-entry .latency {
            color: #888;
            text-align: right;
        }
        .distribution {
            background: #2a2a2a;
            border: 1px solid #3a3a3a;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
        }
        .distribution h2 {
            font-size: 1.2rem;
            margin-bottom: 16px;
            color: #e0e0e0;
        }
        .dist-entry {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #3a3a3a;
            font-size: 0.9rem;
        }
        .dist-entry:last-child {
            border-bottom: none;
            font-weight: 600;
            margin-top: 8px;
            padding-top: 12px;
            border-top: 2px solid #3a3a3a;
        }
        .dist-entry .server {
            color: #667eea;
            font-family: monospace;
            font-size: 0.85rem;
        }
        .dist-entry .count {
            color: #e0e0e0;
        }
        .dist-entry .percent {
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Get-Back Dashboard</h1>
        <p class="subtitle">
            Dual-Protocol Counter Service
            <span class="status" id="status">● LIVE</span>
        </p>

        <div class="metrics">
            <div class="metric http">
                <div class="metric-label">HTTP Counter</div>
                <div class="metric-value" id="http-counter">-</div>
                <div class="metric-delta" id="http-delta"></div>
            </div>
            <div class="metric tcp">
                <div class="metric-label">TCP Counter</div>
                <div class="metric-value" id="tcp-counter">-</div>
                <div class="metric-delta" id="tcp-delta"></div>
            </div>
            <div class="metric">
                <div class="metric-label">Uptime</div>
                <div class="metric-value" id="uptime">-</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value" id="total">-</div>
            </div>
        </div>

        <div class="config">
            <h2>Backend Configuration</h2>
            <div class="config-row">
                <label>HTTP Backend:</label>
                <input type="text" id="http-backend" placeholder="hostname:9091">
                <span></span>
            </div>
            <div class="config-row">
                <label>TCP Backend:</label>
                <input type="text" id="tcp-backend" placeholder="hostname:9092">
                <span></span>
            </div>
            <div class="config-row">
                <label>Amount:</label>
                <input type="number" id="amount" min="1" max="100" value="10" style="width: 100px;">
                <span style="color: #666; font-size: 0.85rem;">requests per click</span>
            </div>
            <div class="config-row">
                <label></label>
                <button onclick="saveConfig()">Save</button>
                <span></span>
            </div>
            <p style="color: #666; font-size: 0.85rem; margin-top: 8px;">
                Examples: <code>getback:9091</code>, <code>backend-canary:9092</code>, <code>localhost:9091</code>
            </p>
        </div>

        <div class="controls">
            <h2>Make Requests</h2>
            <div class="button-group">
                <label>HTTP:</label>
                <button class="http" onclick="makeRequest('http')">Send HTTP Request</button>
            </div>
            <div class="button-group">
                <label>TCP:</label>
                <button class="tcp" onclick="makeRequest('tcp', 'test')">Immediate (test)</button>
                <button class="tcp secondary" onclick="makeRequest('tcp', '2')">Timed (2s)</button>
                <button class="tcp secondary" onclick="makeRequest('tcp', 'OPEN')">Persistent (OPEN)</button>
            </div>
        </div>

        <div class="distribution">
            <h2>Request Distribution <button onclick="clearDistribution()" style="float: right; padding: 4px 12px; font-size: 0.8rem;">Clear</button></h2>
            <div id="distribution">
                <p style="color: #888; text-align: center;">No requests yet</p>
            </div>
        </div>

        <div class="history">
            <h2>Request History (Last 20) <button onclick="clearHistory()" style="float: right; padding: 4px 12px; font-size: 0.8rem;">Clear</button></h2>
            <div id="history">
                <p style="color: #888; text-align: center;">No requests yet</p>
            </div>
        </div>

        <div class="footer">
            Auto-refreshing every 1 second • Get-Back v1.0.0
        </div>
    </div>

    <script>
        // Default backend from server configuration
        const DEFAULT_BACKEND_HOST = '__BACKEND_HOST__';

        let lastHttpCounter = 0;
        let lastTcpCounter = 0;

        function formatUptime(seconds) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            if (h > 0) return `${h}h ${m}m`;
            if (m > 0) return `${m}m ${s}s`;
            return `${s}s`;
        }

        async function updateMetrics() {
            try {
                const response = await fetch('/stats');
                const data = await response.json();

                // Update counter values
                document.getElementById('http-counter').textContent = data.http_counter;
                document.getElementById('tcp-counter').textContent = data.tcp_counter;
                document.getElementById('uptime').textContent = formatUptime(data.uptime);
                document.getElementById('total').textContent =
                    data.http_counter + data.tcp_counter;

                // Calculate deltas
                const httpDelta = data.http_counter - lastHttpCounter;
                const tcpDelta = data.tcp_counter - lastTcpCounter;

                if (httpDelta > 0) {
                    document.getElementById('http-delta').textContent = `+${httpDelta} req/s`;
                }
                if (tcpDelta > 0) {
                    document.getElementById('tcp-delta').textContent = `+${tcpDelta} req/s`;
                }

                lastHttpCounter = data.http_counter;
                lastTcpCounter = data.tcp_counter;

                document.getElementById('status').textContent = '● LIVE';
            } catch (error) {
                document.getElementById('status').textContent = '● ERROR';
                console.error('Failed to fetch metrics:', error);
            }
        }

        // State for history and distribution (load from localStorage)
        let requestHistory = [];
        let serverCounts = {};

        // Load persisted state from localStorage
        try {
            const savedHistory = localStorage.getItem('requestHistory');
            const savedCounts = localStorage.getItem('serverCounts');
            if (savedHistory) requestHistory = JSON.parse(savedHistory);
            if (savedCounts) serverCounts = JSON.parse(savedCounts);
        } catch (e) {
            console.error('Failed to load state:', e);
        }

        // Save state to localStorage
        function saveState() {
            localStorage.setItem('requestHistory', JSON.stringify(requestHistory));
            localStorage.setItem('serverCounts', JSON.stringify(serverCounts));
        }

        // Initialize UI from localStorage on page load
        function initConfig() {
            const httpBackend = localStorage.getItem('httpBackend') || `${DEFAULT_BACKEND_HOST}:9091`;
            const tcpBackend = localStorage.getItem('tcpBackend') || `${DEFAULT_BACKEND_HOST}:9092`;
            const amount = parseInt(localStorage.getItem('amount') || '10');
            document.getElementById('http-backend').value = httpBackend;
            document.getElementById('tcp-backend').value = tcpBackend;
            document.getElementById('amount').value = amount;

            // Update UI with persisted state
            updateHistory();
            updateDistribution();
        }

        // Read current configuration from input fields
        function getConfig() {
            return {
                httpBackend: document.getElementById('http-backend').value,
                tcpBackend: document.getElementById('tcp-backend').value,
                amount: parseInt(document.getElementById('amount').value) || 10
            };
        }

        // Save backend configuration to localStorage
        function saveConfig() {
            const config = getConfig();
            localStorage.setItem('httpBackend', config.httpBackend);
            localStorage.setItem('tcpBackend', config.tcpBackend);
            localStorage.setItem('amount', config.amount);
            alert('Backend configuration saved!');
        }

        // Initialize configuration on page load
        initConfig();

        async function makeSingleRequest(protocol, command, backend) {
            const url = protocol === 'http' ? '/api/request/http' : '/api/request/tcp';
            const bodyData = protocol === 'tcp'
                ? { command: command || 'test', backend }
                : { backend };

            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyData)
            });
            return await response.json();
        }

        async function makeRequest(protocol, command = null) {
            const config = getConfig();
            const backend = protocol === 'http' ? config.httpBackend : config.tcpBackend;
            const amount = config.amount;

            try {
                // Create array of N concurrent requests
                const requests = Array.from({ length: amount }, () =>
                    makeSingleRequest(protocol, command, backend)
                );

                // Execute all requests concurrently
                const results = await Promise.all(requests);

                // Process all results
                results.forEach(data => {
                    // Add to history (keep last 20)
                    const entry = {
                        protocol,
                        counter: data.counter,
                        server: data.server,
                        latency: data.latency_ms,
                        command: data.command,
                        timestamp: new Date().toLocaleTimeString()
                    };
                    requestHistory.unshift(entry);
                    if (requestHistory.length > 20) requestHistory.pop();

                    // Update server counts
                    serverCounts[data.server] = (serverCounts[data.server] || 0) + 1;
                });

                // Update UI once after all requests complete
                updateHistory();
                updateDistribution();
                updateMetrics();

                // Persist state to localStorage
                saveState();

            } catch (error) {
                console.error('Request failed:', error);
            }
        }

        function updateHistory() {
            const historyEl = document.getElementById('history');
            if (requestHistory.length === 0) {
                historyEl.innerHTML = '<p style="color: #888; text-align: center;">No requests yet</p>';
                return;
            }

            historyEl.innerHTML = requestHistory.map(entry => {
                const details = entry.protocol === 'tcp' && entry.command
                    ? `Counter: ${entry.counter} | Command: ${entry.command}`
                    : `Counter: ${entry.counter}`;

                return `
                    <div class="history-entry">
                        <span class="time">${entry.timestamp}</span>
                        <span>
                            <span class="protocol ${entry.protocol}">${entry.protocol.toUpperCase()}</span>
                            <span class="details">${details}</span>
                            <span class="server">${entry.server}</span>
                        </span>
                        <span class="latency">${entry.latency}ms</span>
                    </div>
                `;
            }).join('');
        }

        function updateDistribution() {
            const distEl = document.getElementById('distribution');
            const servers = Object.keys(serverCounts);

            if (servers.length === 0) {
                distEl.innerHTML = '<p style="color: #888; text-align: center;">No requests yet</p>';
                return;
            }

            const total = Object.values(serverCounts).reduce((a, b) => a + b, 0);
            const entries = servers.map(server => {
                const count = serverCounts[server];
                const percent = Math.round((count / total) * 100);
                return { server, count, percent };
            }).sort((a, b) => b.count - a.count);

            distEl.innerHTML = entries.map(e => `
                <div class="dist-entry">
                    <span class="server">${e.server}</span>
                    <span class="count">${e.count} requests</span>
                    <span class="percent">(${e.percent}%)</span>
                </div>
            `).join('') + `
                <div class="dist-entry">
                    <span>Total</span>
                    <span class="count">${total} requests</span>
                    <span></span>
                </div>
            `;
        }

        // Clear distribution data
        function clearDistribution() {
            if (confirm('Clear distribution data? This will reset all server counts.')) {
                serverCounts = {};
                updateDistribution();
                saveState();
            }
        }

        // Clear history data
        function clearHistory() {
            if (confirm('Clear request history?')) {
                requestHistory = [];
                updateHistory();
                saveState();
            }
        }

        // Update immediately and then every second
        updateMetrics();
        setInterval(updateMetrics, 1000);
    </script>
</body>
</html>
"""
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
            port = int(port_str)
            if 1 <= port <= 65535 and host.strip():
                return (host.strip(), port)
    except (ValueError, AttributeError):
        pass

    return (default_host, default_port)


def format_stats_json(
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float
) -> str:
    """Format stats as JSON.

    Args:
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp

    Returns:
        JSON string with current stats
    """
    stats = {
        "http_counter": http_counter._value,
        "tcp_counter": tcp_counter._value,
        "uptime": int(time.time() - start_time),
        "timestamp": int(time.time())
    }
    return json.dumps(stats)


async def make_http_request(backend_host: str = 'localhost', backend_port: int = 9091) -> Dict[str, Any]:
    """Make HTTP request to backend server.

    Args:
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9091)

    Returns:
        Dict with counter, server, latency_ms, timestamp
    """
    start = time.time()
    reader, writer = await asyncio.open_connection(backend_host, backend_port)

    try:
        # Send HTTP request
        request = b"GET / HTTP/1.0\r\n\r\n"
        writer.write(request)
        await writer.drain()

        # Read response
        response = await reader.read(1024)
        response_text = response.decode('utf-8')

        # Parse response body (skip headers)
        body = response_text.split('\r\n\r\n', 1)[1].strip()

        # Parse "N (server_id)" format
        parts = body.split(' (', 1)
        counter = int(parts[0])
        server = parts[1].rstrip(')') if len(parts) > 1 else "unknown"

        latency_ms = int((time.time() - start) * 1000)

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "timestamp": int(time.time())
        }
    finally:
        writer.close()
        await writer.wait_closed()


async def make_tcp_request(command: str = "test", backend_host: str = 'localhost', backend_port: int = 9092) -> Dict[str, Any]:
    """Make TCP request to backend server.

    Args:
        command: TCP command to send
        backend_host: Backend host to connect to (default: localhost)
        backend_port: Backend port to connect to (default: 9092)

    Returns:
        Dict with counter, server, latency_ms, command, timestamp
    """
    start = time.time()
    reader, writer = await asyncio.open_connection(backend_host, backend_port)

    try:
        # Send TCP command
        writer.write(f"{command}\n".encode('utf-8'))
        await writer.drain()

        # Read response
        response = await reader.readline()
        response_text = response.decode('utf-8').strip()

        # Parse "N (server_id)" format
        parts = response_text.split(' (', 1)
        counter = int(parts[0])
        server = parts[1].rstrip(')') if len(parts) > 1 else "unknown"

        latency_ms = int((time.time() - start) * 1000)

        return {
            "counter": counter,
            "server": server,
            "latency_ms": latency_ms,
            "command": command,
            "timestamp": int(time.time())
        }
    finally:
        writer.close()
        await writer.wait_closed()


async def dashboard_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    http_counter: Counter,
    tcp_counter: Counter,
    start_time: float,
    backend_host: str
) -> None:
    """Handle dashboard HTTP requests.

    Args:
        reader: Async stream reader
        writer: Async stream writer
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests
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

        # Parse Content-Length for POST requests
        content_length = 0
        for line in request_text.split('\r\n')[1:]:
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())
                break

        # Read request body if present
        request_body = ""
        if content_length > 0:
            body_data = await reader.readexactly(content_length)
            request_body = body_data.decode('utf-8')

        if path == "/api/request/http" and method == "POST":
            # Make HTTP request to backend
            # Parse backend from request body or use default
            req_backend = backend_host
            req_port = 9091
            if request_body:
                try:
                    body_json = json.loads(request_body)
                    if 'backend' in body_json:
                        req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9091)
                except json.JSONDecodeError:
                    pass

            result = await make_http_request(req_backend, req_port)
            body = json.dumps(result)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/api/request/tcp" and method == "POST":
            # Make TCP request to backend
            command = "test"
            req_backend = backend_host
            req_port = 9092
            if request_body:
                try:
                    body_json = json.loads(request_body)
                    command = body_json.get("command", "test")
                    if 'backend' in body_json:
                        req_backend, req_port = parse_backend(body_json['backend'], backend_host, 9092)
                except json.JSONDecodeError:
                    pass

            result = await make_tcp_request(command, req_backend, req_port)
            body = json.dumps(result)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        elif path == "/stats":
            # JSON stats endpoint
            body = format_stats_json(http_counter, tcp_counter, start_time)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "\r\n"
                f"{body}\n"
            ).encode('utf-8')

        else:
            # Dashboard HTML (root or /dashboard)
            html = render_dashboard_html(backend_host)
            response = (
                "HTTP/1.0 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "\r\n"
                f"{html}"
            ).encode('utf-8')

        writer.write(response)
        await writer.drain()

    except asyncio.IncompleteReadError:
        logger.warning(f"Dashboard incomplete request from {addr}")
    except Exception as e:
        logger.error(f"Dashboard error from {addr}: {e}")
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
    backend_host: str = 'localhost'
) -> None:
    """Start dashboard server.

    Args:
        host: Bind address
        port: Port number (typically 9093)
        http_counter: HTTP counter instance
        tcp_counter: TCP counter instance
        start_time: Server start timestamp
        backend_host: Backend host for making requests (default: localhost)
    """
    async def handler(reader, writer):
        await dashboard_handler(reader, writer, http_counter, tcp_counter, start_time, backend_host)

    server = await asyncio.start_server(handler, host, port)
    addr = server.sockets[0].getsockname()
    logger.info(f"✓ Dashboard ready at http://{addr[0]}:{addr[1]}/")

    async with server:
        await server.serve_forever()
