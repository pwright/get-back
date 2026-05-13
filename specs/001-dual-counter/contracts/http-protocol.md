# HTTP Protocol Contract

**Version**: 1.0
**Protocol**: HTTP/1.0
**Port**: 9091 (configurable)

## Overview

Simple HTTP endpoint that returns an incrementing counter value for each request. Protocol-agnostic - any HTTP method, any path accepted.

## Endpoints

### Counter Endpoint (Any Path Except `/health`)

Increments counter and returns value.

### Health Endpoint (`/health`)

Special endpoint for Kubernetes liveness/readiness probes. Does NOT increment counter.

**Request**:
```http
GET /health HTTP/1.1
Host: localhost:9091

```

**Response**:
```http
HTTP/1.0 200 OK

OK
```

**Behavior**:
- Always returns 200 OK (unless server is completely down)
- Does NOT increment counter
- Lightweight check (no business logic)
- Used by orchestration systems (Kubernetes, load balancers)

## Request Format

**Any HTTP Request (Except `/health`)**:
```http
GET / HTTP/1.1
Host: localhost:9091

```

Or:
```http
POST /anything HTTP/1.0

```

**Request Handling**:
- Method: Any (GET, POST, PUT, etc.) - all treated identically
- Path: Any - all paths return counter
- Headers: Ignored (not parsed beyond finding end of request)
- Body: Ignored

**Parsing**: Server reads until `\r\n\r\n` (blank line) indicating end of headers

## Response Format

**Success Response**:
```http
HTTP/1.0 200 OK

{counter}
```

Where `{counter}` is a positive integer (1, 2, 3, ...).

**Example**:
```http
HTTP/1.0 200 OK

42
```

**Response Components**:
- Status line: `HTTP/1.0 200 OK\r\n`
- Blank line: `\r\n`
- Body: Integer counter value
- Newline after body: `\n` (for readability)

**No Error Responses**: Server always returns 200 OK if connection accepted. Malformed requests treated as valid requests.

## Behavior

### Counter Increment
- Counter increments atomically for each request
- HTTP counter is independent of TCP counter
- Counter starts at 1 on server start
- No maximum value - wraps at integer limit (not expected in practice)

### Connection Lifecycle
1. Client connects
2. Client sends HTTP request
3. Server increments HTTP counter
4. Server responds with counter value
5. **Server closes connection immediately**
6. Connection state: `TIME_WAIT` on server side (TCP standard)

### Concurrency
- Multiple concurrent requests each get unique counter values
- No duplicate values
- No skipped values under normal operation
- Counter increment is atomic (thread-safe)

## Examples

### Example 1: First Request
**Request**:
```http
GET / HTTP/1.1
Host: localhost:9091

```

**Response**:
```http
HTTP/1.0 200 OK

1
```

### Example 2: Subsequent Request
**Request**:
```http
GET /api/count HTTP/1.1
Host: localhost:9091

```

**Response**:
```http
HTTP/1.0 200 OK

2
```

### Example 3: POST Request (Same Behavior)
**Request**:
```http
POST /anything HTTP/1.1
Host: localhost:9091
Content-Length: 10

some data
```

**Response**:
```http
HTTP/1.0 200 OK

3
```

### Example 4: curl Usage
```bash
$ curl http://localhost:9091/
1

$ curl http://localhost:9091/anything
2

$ curl -X POST http://localhost:9091/
3
```

## Client Implementation Notes

### Minimal Client (Python urllib)
```python
from urllib.request import urlopen

response = urlopen('http://localhost:9091/')
counter = response.read().decode('utf-8').strip()
print(f"Counter: {counter}")
```

### With Error Handling
```python
import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen('http://localhost:9091/', timeout=5)
    counter = response.read().decode('utf-8').strip()
    print(f"Counter: {counter}")
except urllib.error.URLError as e:
    print(f"Error: {e}")
except TimeoutError:
    print("Request timed out")
```

## Load Balancer Testing

### Scenario: Round-Robin Load Balancing
```bash
# Setup: 3 backend servers on ports 9091, 9191, 9291
# Load balancer on port 8080 distributing round-robin

$ curl http://lb:8080/  # Backend 1, counter: 1
1
$ curl http://lb:8080/  # Backend 2, counter: 1
1
$ curl http://lb:8080/  # Backend 3, counter: 1
1
$ curl http://lb:8080/  # Backend 1, counter: 2
2
$ curl http://lb:8080/  # Backend 2, counter: 2
2
```

**Expected Pattern**: Each backend counter increments independently, demonstrating distribution.

### Scenario: Least Connections
With HTTP/1.0 immediate close, least connections behaves like round-robin since no persistent connections exist.

## Error Conditions

### Server Not Running
- Client receives: `Connection refused` (ECONNREFUSED)
- No HTTP response received

### Port in Use
- Server fails to start with bind error
- Logged and process exits

### Client Disconnect Mid-Request
- Server logs connection reset
- Counter not incremented (request not complete)

### Malformed HTTP
- Server treats any data followed by `\r\n\r\n` as valid
- Always responds with counter

## Performance Characteristics

**Expected Latency**:
- <10ms for local requests (localhost)
- <100ms for LAN requests
- Network latency + minimal processing time

**Throughput**:
- Designed for demonstration, not high performance
- Expected: 100+ req/s on modest hardware
- Bottleneck: asyncio event loop, not counter logic

**Resource Usage**:
- ~4KB memory per concurrent connection
- Connections closed immediately, minimal sustained load

## Version Compatibility

**HTTP/1.0 vs HTTP/1.1**:
- Server responds with HTTP/1.0 (no chunking, no persistent connections)
- Accepts both HTTP/1.0 and HTTP/1.1 requests
- Always closes connection (Connection: close implied)

**HTTP/2, HTTP/3**:
- Not supported
- Clients fall back to HTTP/1.1 (standard behavior)

## Security Considerations

**Not Production-Ready**:
- No authentication
- No rate limiting
- No input validation
- Binds to 0.0.0.0 (all interfaces) by default

**Intended Use**: Demonstration and testing only, not for production traffic.

## Logging

**Events Logged** (INFO level):
- Server startup: `HTTP server listening on {host}:{port}`
- Request received: `HTTP request from {remote_addr}`
- Counter incremented: `HTTP counter: {value}`
- Connection closed: `HTTP connection closed: {remote_addr}`

**Debug Level**:
- Raw request data (first 200 chars)
- Response sent
- Timing information
