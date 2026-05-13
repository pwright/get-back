# Research: Dual-Protocol Counter Service

**Phase**: 0 - Outline & Research
**Date**: 2026-05-13
**Feature**: Dual-Protocol Counter Service

## Research Areas

### 1. Concurrent Server Architecture (asyncio)

**Decision**: Use Python asyncio with `asyncio.start_server()` for TCP and `asyncio.web.Application` OR custom HTTP handler

**Rationale**:
- asyncio is Python standard library (no dependencies)
- Native support for concurrent TCP servers via `asyncio.start_server()`
- Event loop naturally handles both TCP and HTTP concurrently
- Eliminates need for threading/multiprocessing complexity
- Excellent debugging support with asyncio debug mode

**Alternatives Considered**:
- **Threading (socketserver.TCPServer + http.server.HTTPServer)**: Rejected because thread overhead, harder to debug race conditions, constitution favors simplicity
- **aiohttp library**: Rejected to maintain zero-dependency constraint, though viable if HTTP complexity grows
- **FastAPI/Flask**: Rejected as unnecessary frameworks per constitution

**Implementation Approach**:
- Single event loop running both servers
- TCP: `asyncio.start_server(tcp_handler, host, tcp_port)`
- HTTP: Custom asyncio protocol OR simple `asyncio.start_server()` with HTTP/1.0 response formatting
- Both servers started with `asyncio.gather()` for concurrent execution

### 2. HTTP Server Implementation

**Decision**: Implement minimal HTTP/1.0 response handler using asyncio StreamReader/StreamWriter

**Rationale**:
- HTTP GET counter response is trivial (1-2 lines of HTTP response)
- Standard library only requirement
- Response format: `HTTP/1.0 200 OK\r\n\r\n{counter}\n`
- No routing, headers, or complex HTTP features needed
- Aligns with simplicity principle

**Alternatives Considered**:
- **http.server.HTTPServer**: Synchronous, would require threading
- **aiohttp**: External dependency, overkill for counter response
- **Custom asyncio-http**: Chosen - simplest for our use case

**Request Handling**:
```
1. Accept connection
2. Read until "\r\n\r\n" (end of HTTP request)
3. Parse path from request line
4. If path == "/health":
   - Write "HTTP/1.0 200 OK\r\n\r\nOK\n" (no counter increment)
5. Else:
   - Increment counter
   - Write "HTTP/1.0 200 OK\r\n\r\n{counter}\n"
6. Close connection
```

**Health Endpoint Rationale**:
- Kubernetes liveness/readiness probes need a lightweight check
- Incrementing counter on health checks would pollute counter values
- `/health` returns 200 OK without business logic
- Enables better orchestration (restart unhealthy pods, route traffic to ready pods)

### 3. TCP Protocol Message Format

**Decision**: Newline-delimited text protocol

**Rationale**:
- Simple to parse and debug
- Works with telnet/nc for manual testing
- Client intent clearly readable in logs
- Python `StreamReader.readline()` handles parsing

**Protocol Specification**:

**Client Request Format**:
- Numeric value: `"5\n"` → stay open 5 seconds
- OPEN command: `"OPEN\n"` → stay open indefinitely  
- Other text: `"anything\n"` → close immediately
- Empty/just newline: `"\n"` → close immediately

**Server Response Format**:
- Response: `"{counter}\n"` where counter is integer
- Send immediately after receiving command
- Then honor timing directive

**Timing Behavior**:
- Numeric: `await asyncio.sleep(seconds)` then close
- OPEN: Keep connection in active set, never auto-close
- Other: Close immediately after sending response

**Error Handling**:
- Invalid number (e.g., "5.5", "999999999999"): Treat as "other" (immediate close)
- No data received (timeout): Close after 30s default keepalive
- Connection reset: Log and cleanup

### 4. Atomic Counter Implementation

**Decision**: Use `asyncio.Lock()` around counter increment

**Rationale**:
- Python GIL doesn't guarantee atomicity for increment operations
- asyncio.Lock() is the idiomatic async synchronization primitive
- Minimal performance impact (<1μs lock acquisition)
- Prevents race conditions when handling concurrent connections

**Alternatives Considered**:
- **No locking (rely on GIL)**: Unsafe, `+=` is not atomic in Python bytecode
- **threading.Lock**: Wrong primitive for asyncio (can block event loop)
- **Queue-based**: Over-engineered for simple increment

**Implementation**:
```python
class Counter:
    def __init__(self):
        self._value = 0
        self._lock = asyncio.Lock()
    
    async def increment(self):
        async with self._lock:
            self._value += 1
            return self._value
```

### 5. Configuration Management

**Decision**: Command-line arguments with environment variable fallback

**Rationale**:
- CLI args: Explicit, visible in process list, easy testing
- Env vars: Docker-friendly, 12-factor app pattern
- Standard library argparse sufficient

**Configuration Items**:
- `--http-port` / `HTTP_PORT` (default: 9091)
- `--tcp-port` / `TCP_PORT` (default: 9092)
- `--host` / `HOST` (default: 0.0.0.0)
- `--log-level` / `LOG_LEVEL` (default: INFO)

**Priority**: CLI args > env vars > defaults

### 6. Logging Strategy

**Decision**: Python standard library `logging` with structured format

**Rationale**:
- Standard library (no dependencies)
- Excellent filtering and formatting
- Multiple handlers (console, file if needed)
- Constitution requires observable behavior

**Log Events**:
- INFO: Server startup (ports, config)
- INFO: Connection accepted (protocol, remote_addr)
- INFO: Counter increment (protocol, new_value, command if TCP)
- INFO: Connection closed (protocol, remote_addr, duration)
- WARNING: Invalid TCP command, malformed requests
- ERROR: Server exceptions, bind failures

**Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

### 7. Testing Strategy

**Decision**: pytest with async support (pytest-asyncio)

**Rationale**:
- Industry standard Python testing framework
- Native async test support via pytest-asyncio
- Excellent fixtures for setup/teardown
- Clear assertion failures

**Test Categories**:

**Unit Tests** (`test_counter.py`):
- Counter increment correctness
- Counter thread-safety (concurrent increments)
- Separate HTTP/TCP counter independence

**Integration Tests** (`test_http_server.py`, `test_tcp_server.py`):
- HTTP: Send requests, verify incrementing responses
- TCP: Test numeric, OPEN, and arbitrary commands
- TCP: Verify connection timing behavior
- Protocol-specific error handling

**End-to-End Tests** (`test_integration.py`):
- Start both servers
- Concurrent HTTP and TCP requests
- Verify counter independence
- Graceful shutdown

**Test Fixtures**:
- Server startup/shutdown
- Test client helpers
- Port allocation (random ports for parallel tests)

### 8. Sample Client Requirements

**Decision**: Provide standalone Python scripts with minimal dependencies

**Rationale**:
- Demonstrates API usage per spec requirement FR-013
- Users can test without reading server code
- Useful for load balancer testing

**Clients to Provide**:

**`clients/http_client.py`**:
- Uses `urllib` (standard library) or `requests` (if acceptable)
- Command: `python clients/http_client.py http://localhost:9091`
- Output: Prints counter value

**`clients/tcp_client.py`**:
- Uses `socket` (standard library)
- Command: `python clients/tcp_client.py localhost 9092 [command]`
- Examples:
  - `python clients/tcp_client.py localhost 9092 5` (5 second connection)
  - `python clients/tcp_client.py localhost 9092 OPEN` (persistent)
  - `python clients/tcp_client.py localhost 9092 hello` (immediate)
- Output: Prints counter value and connection duration

**`clients/README.md`**:
- Usage examples for both clients
- Load balancer testing scenarios
- Example: Round-robin vs least-connections demonstration

### 9. Deployment Considerations

**Decision**: Provide Dockerfile, document bare-metal and container deployment

**Rationale**:
- Container is standard deployment model
- Bare-metal useful for development/debugging
- Constitution: simple deployment (SC-005)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY getback/ getback/
COPY clients/ clients/
CMD ["python", "-m", "getback"]
```

**Bare-metal**:
```bash
python -m getback --http-port 9091 --tcp-port 9092
```

### 10. Python Version Selection

**Decision**: Python 3.11+ required

**Rationale**:
- asyncio maturity and performance improvements in 3.11
- Exception groups (useful for multi-server error handling)
- Better error messages (helpful for debugging)
- Widely available (Ubuntu 23.04+, current macOS/Windows)

**Not 3.10**: Fewer asyncio improvements
**Not 3.12/3.13**: Too cutting-edge, may limit deployment targets

## Summary of Technical Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Language | Python 3.11+ | Rapid iteration, excellent debugging |
| Concurrency | asyncio (single event loop) | Standard library, simple mental model |
| HTTP Server | Custom asyncio handler | Zero dependencies, <50 LOC |
| TCP Protocol | Newline-delimited text | Human-readable, debuggable with telnet |
| Testing Console | Port 9093, interactive UI + API | Self-contained demo tool, no external clients needed |
| Server Identity | Hostname from HOSTNAME env or socket | Kubernetes-friendly, enables LB observation |
| Counter | asyncio.Lock-protected increment | Safe, simple, idiomatic |
| Config | CLI args + env vars | Flexible, 12-factor compliant |
| Logging | Standard library logging | Observable, structured, filterable |
| Testing | pytest + pytest-asyncio | Industry standard, async support |
| Deployment | Docker + bare-metal docs | Flexible deployment options |

## Open Questions / Future Refinements

None - all Technical Context "NEEDS CLARIFICATION" items resolved. Proceed to Phase 1 design.
