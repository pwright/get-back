# Implementation Tasks: Dual-Protocol Counter Service

**Feature**: Dual-Protocol Counter Service  
**Branch**: `001-dual-counter`  
**Date**: 2026-05-13

## Task Breakdown

Tasks are organized by priority and dependencies. Each task is independently testable.

---

## Phase 1: Core Infrastructure (P1)

### Task 1.1: Project Structure Setup
**Priority**: P1  
**Estimated**: 15 min  
**Dependencies**: None

**Description**: Create package directory structure and empty module files.

**Acceptance Criteria**:
- [ ] `getback/` directory exists with `__init__.py`
- [ ] Empty modules: `counter.py`, `http_server.py`, `tcp_server.py`, `config.py`, `cli.py`, `__main__.py`
- [ ] `clients/` directory created
- [ ] `tests/` directory with `conftest.py`
- [ ] `requirements.txt` and `requirements-dev.txt` created

**Files to Create**:
```
getback/__init__.py
getback/__main__.py
getback/counter.py
getback/http_server.py
getback/tcp_server.py
getback/config.py
getback/cli.py
clients/
tests/conftest.py
requirements.txt
requirements-dev.txt
```

---

### Task 1.2: Atomic Counter Implementation
**Priority**: P1  
**Estimated**: 30 min  
**Dependencies**: Task 1.1

**Description**: Implement thread-safe counter with asyncio.Lock.

**Acceptance Criteria**:
- [ ] `Counter` class in `getback/counter.py`
- [ ] `__init__()` initializes value to 0 and creates asyncio.Lock
- [ ] `async def increment()` returns new value atomically
- [ ] `async def get()` returns current value without incrementing
- [ ] Unit tests in `tests/test_counter.py` verify atomicity

**Implementation Notes**:
```python
# getback/counter.py
import asyncio

class Counter:
    def __init__(self):
        self._value = 0
        self._lock = asyncio.Lock()
    
    async def increment(self) -> int:
        async with self._lock:
            self._value += 1
            return self._value
    
    async def get(self) -> int:
        async with self._lock:
            return self._value
```

**Tests**: Concurrent increment test (100 tasks incrementing simultaneously)

---

### Task 1.3: Configuration Management
**Priority**: P1  
**Estimated**: 30 min  
**Dependencies**: Task 1.1

**Description**: Implement configuration loading from CLI args and env vars.

**Acceptance Criteria**:
- [ ] `Config` dataclass in `getback/config.py`
- [ ] Fields: `http_port`, `tcp_port`, `host`, `log_level`
- [ ] Defaults: HTTP 9091, TCP 9092, host 0.0.0.0, log_level INFO
- [ ] `load_config()` function reads from env vars and returns Config
- [ ] Unit tests verify env var precedence

**Implementation Notes**:
```python
# getback/config.py
from dataclasses import dataclass
import os

@dataclass
class Config:
    http_port: int = 9091
    tcp_port: int = 9092
    host: str = "0.0.0.0"
    log_level: str = "INFO"

def load_config() -> Config:
    return Config(
        http_port=int(os.getenv('HTTP_PORT', '9091')),
        tcp_port=int(os.getenv('TCP_PORT', '9092')),
        host=os.getenv('HOST', '0.0.0.0'),
        log_level=os.getenv('LOG_LEVEL', 'INFO')
    )
```

---

### Task 1.4: CLI Argument Parsing
**Priority**: P1  
**Estimated**: 30 min  
**Dependencies**: Task 1.3

**Description**: Implement CLI with argparse, override config from args.

**Acceptance Criteria**:
- [ ] `parse_args()` function in `getback/cli.py`
- [ ] Arguments: `--http-port`, `--tcp-port`, `--host`, `--log-level`
- [ ] Returns Config object with CLI args overriding env vars
- [ ] Help text describes each argument
- [ ] Unit tests verify CLI precedence over env vars

---

## Phase 2: HTTP Server (P1)

### Task 2.1: HTTP Request Parser
**Priority**: P1  
**Estimated**: 45 min  
**Dependencies**: Task 1.1

**Description**: Parse HTTP request line to extract path.

**Acceptance Criteria**:
- [ ] `parse_http_request(data: bytes) -> str` in `getback/http_server.py`
- [ ] Extracts path from "GET /path HTTP/1.1" format
- [ ] Returns "/" for empty path
- [ ] Returns "/health" for health endpoint
- [ ] Handles malformed requests gracefully (return "/" as default)
- [ ] Unit tests for various request formats

**Implementation Notes**:
```python
def parse_http_request(data: bytes) -> str:
    try:
        request_line = data.decode('utf-8').split('\r\n')[0]
        parts = request_line.split(' ')
        if len(parts) >= 2:
            return parts[1]  # e.g., "GET /health HTTP/1.1" -> "/health"
    except:
        pass
    return "/"
```

---

### Task 2.2: HTTP Response Formatter
**Priority**: P1  
**Estimated**: 15 min  
**Dependencies**: Task 1.1

**Description**: Format HTTP/1.0 responses.

**Acceptance Criteria**:
- [ ] `format_http_response(body: str) -> bytes` in `getback/http_server.py`
- [ ] Returns `b"HTTP/1.0 200 OK\r\n\r\n{body}\n"`
- [ ] Unit tests verify format

---

### Task 2.3: HTTP Server Implementation
**Priority**: P1  
**Estimated**: 1 hour  
**Dependencies**: Tasks 1.2, 2.1, 2.2

**Description**: Implement asyncio HTTP server with counter and health endpoint.

**Acceptance Criteria**:
- [ ] `async def http_handler(reader, writer, counter)` handles connections
- [ ] Reads until `\r\n\r\n` (end of request)
- [ ] Parses path from request
- [ ] `/health` returns "OK" without incrementing
- [ ] Other paths increment counter and return value
- [ ] Logs connection events (INFO level)
- [ ] `async def start_http_server(host, port, counter)` starts server
- [ ] Integration test: start server, send requests, verify counter increments
- [ ] Integration test: `/health` doesn't increment counter

**Implementation Notes**:
```python
async def http_handler(reader, writer, counter, logger):
    addr = writer.get_extra_info('peername')
    logger.info(f"HTTP connection from {addr}")
    
    try:
        data = await reader.readuntil(b'\r\n\r\n')
        path = parse_http_request(data)
        
        if path == '/health':
            body = "OK"
        else:
            value = await counter.increment()
            logger.info(f"HTTP counter: {value}")
            body = str(value)
        
        response = format_http_response(body)
        writer.write(response)
        await writer.drain()
    except Exception as e:
        logger.error(f"HTTP error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info(f"HTTP connection closed: {addr}")
```

---

## Phase 3: TCP Server (P1)

### Task 3.1: TCP Command Parser
**Priority**: P1  
**Estimated**: 30 min  
**Dependencies**: Task 1.1

**Description**: Parse TCP command and determine connection lifetime.

**Acceptance Criteria**:
- [ ] `parse_tcp_command(data: str) -> tuple[str, Optional[int]]` in `getback/tcp_server.py`
- [ ] Returns `("timed", N)` for numeric commands
- [ ] Returns `("persistent", None)` for "OPEN"
- [ ] Returns `("immediate", 0)` for other commands
- [ ] Handles invalid numbers (non-int) as immediate
- [ ] Unit tests for all command types

**Implementation Notes**:
```python
def parse_tcp_command(data: str) -> tuple[str, Optional[int]]:
    command = data.strip()
    
    if command == "OPEN":
        return ("persistent", None)
    
    try:
        duration = int(command)
        if duration > 0:
            return ("timed", duration)
    except ValueError:
        pass
    
    return ("immediate", 0)
```

---

### Task 3.2: TCP Server Implementation
**Priority**: P1  
**Estimated**: 1 hour  
**Dependencies**: Tasks 1.2, 3.1

**Description**: Implement asyncio TCP server with command protocol.

**Acceptance Criteria**:
- [ ] `async def tcp_handler(reader, writer, counter, active_connections)` handles connections
- [ ] Reads line (until `\n`)
- [ ] Parses command and determines lifetime
- [ ] Increments counter and responds with value
- [ ] Honors timing: immediate close, sleep N seconds, or add to active set
- [ ] Logs connection events with command and duration
- [ ] `async def start_tcp_server(host, port, counter, active_connections)` starts server
- [ ] Integration test: numeric command → verify duration ±200ms
- [ ] Integration test: OPEN command → verify connection stays open
- [ ] Integration test: arbitrary command → verify immediate close

**Implementation Notes**:
```python
async def tcp_handler(reader, writer, counter, active_connections, logger):
    addr = writer.get_extra_info('peername')
    logger.info(f"TCP connection from {addr}")
    
    try:
        data = await reader.readline()
        command = data.decode('utf-8')
        logger.info(f"TCP command from {addr}: {command.strip()}")
        
        mode, duration = parse_tcp_command(command)
        value = await counter.increment()
        logger.info(f"TCP counter: {value} (mode: {mode})")
        
        response = f"{value}\n".encode('utf-8')
        writer.write(response)
        await writer.drain()
        
        if mode == "timed":
            await asyncio.sleep(duration)
        elif mode == "persistent":
            active_connections.add(writer)
            # Wait until connection closed by client
            await reader.read()  # Blocks until client closes
            active_connections.remove(writer)
    except Exception as e:
        logger.error(f"TCP error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info(f"TCP connection closed: {addr}")
```

---

## Phase 4: Main Application (P1)

### Task 4.1: Logging Setup
**Priority**: P1  
**Estimated**: 15 min  
**Dependencies**: Task 1.3

**Description**: Configure Python logging based on config.

**Acceptance Criteria**:
- [ ] `setup_logging(level: str)` in `getback/__init__.py`
- [ ] Configures root logger with format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- [ ] Sets log level from config
- [ ] Returns logger instance
- [ ] Manual test: verify logs appear with correct format

---

### Task 4.2: Main Entry Point
**Priority**: P1  
**Estimated**: 45 min  
**Dependencies**: Tasks 1.2, 1.4, 2.3, 3.2, 4.1

**Description**: Implement `__main__.py` to start both servers concurrently.

**Acceptance Criteria**:
- [ ] `async def main()` in `getback/__main__.py`
- [ ] Parses CLI args
- [ ] Sets up logging
- [ ] Creates two Counter instances (HTTP and TCP)
- [ ] Starts both servers with `asyncio.gather()`
- [ ] Handles Ctrl+C gracefully (closes active connections)
- [ ] Logs startup message with ports
- [ ] Manual test: `python -m getback` starts both servers
- [ ] Manual test: Ctrl+C shuts down cleanly

**Implementation Notes**:
```python
# getback/__main__.py
import asyncio
from .cli import parse_args
from .counter import Counter
from .http_server import start_http_server
from .tcp_server import start_tcp_server
from . import setup_logging

async def main():
    config = parse_args()
    logger = setup_logging(config.log_level)
    
    logger.info("Starting Dual-Protocol Counter Service")
    
    http_counter = Counter()
    tcp_counter = Counter()
    active_connections = set()
    
    try:
        await asyncio.gather(
            start_http_server(config.host, config.http_port, http_counter, logger),
            start_tcp_server(config.host, config.tcp_port, tcp_counter, active_connections, logger)
        )
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        for conn in active_connections:
            conn.close()
    
if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 5: Sample Clients (P2)

### Task 5.1: HTTP Client
**Priority**: P2  
**Estimated**: 20 min  
**Dependencies**: Task 2.3

**Description**: Simple HTTP client using urllib.

**Acceptance Criteria**:
- [ ] `clients/http_client.py` accepts URL as argument
- [ ] Sends GET request
- [ ] Prints counter value
- [ ] Usage: `python clients/http_client.py http://localhost:9091`
- [ ] Manual test: run client, verify output

---

### Task 5.2: TCP Client
**Priority**: P2  
**Estimated**: 30 min  
**Dependencies**: Task 3.2

**Description**: TCP client supporting all command types.

**Acceptance Criteria**:
- [ ] `clients/tcp_client.py` accepts host, port, command
- [ ] Connects, sends command, receives response
- [ ] Prints counter and connection duration
- [ ] Usage: `python clients/tcp_client.py localhost 9092 [command]`
- [ ] Manual test: numeric command → verify timing
- [ ] Manual test: OPEN → verify persistent connection
- [ ] Manual test: arbitrary → verify immediate close

---

### Task 5.3: Client Documentation
**Priority**: P2  
**Estimated**: 15 min  
**Dependencies**: Tasks 5.1, 5.2

**Description**: Create `clients/README.md` with usage examples.

**Acceptance Criteria**:
- [ ] Usage examples for both clients
- [ ] Load balancer testing scenarios
- [ ] Example outputs

---

## Phase 6: Testing (P1)

### Task 6.1: Unit Tests
**Priority**: P1  
**Estimated**: 1 hour  
**Dependencies**: Tasks 1.2, 1.3, 2.1, 3.1

**Description**: Unit tests for all modules.

**Acceptance Criteria**:
- [ ] `tests/test_counter.py`: Counter atomicity (100 concurrent increments)
- [ ] `tests/test_config.py`: Config loading, env var precedence
- [ ] `tests/test_http_server.py`: HTTP parser, response formatter
- [ ] `tests/test_tcp_server.py`: TCP command parser
- [ ] All tests pass
- [ ] Coverage >80% for covered modules

---

### Task 6.2: Integration Tests
**Priority**: P1  
**Estimated**: 1.5 hours  
**Dependencies**: Tasks 2.3, 3.2, 4.2

**Description**: End-to-end integration tests.

**Acceptance Criteria**:
- [ ] `tests/test_integration.py` with fixtures to start servers
- [ ] Test: HTTP requests increment HTTP counter
- [ ] Test: TCP requests increment TCP counter
- [ ] Test: Counters are independent
- [ ] Test: `/health` doesn't increment counter
- [ ] Test: TCP numeric command timing
- [ ] Test: TCP OPEN command persistence
- [ ] Test: Concurrent requests (10 concurrent HTTP + TCP)
- [ ] All tests pass

---

### Task 6.3: pytest Configuration
**Priority**: P1  
**Estimated**: 15 min  
**Dependencies**: Task 1.1

**Description**: Configure pytest with asyncio support.

**Acceptance Criteria**:
- [ ] `requirements-dev.txt` includes pytest, pytest-asyncio, pytest-cov
- [ ] `pytest.ini` or `pyproject.toml` configures asyncio mode
- [ ] `tests/conftest.py` has fixtures for test servers on random ports
- [ ] `pytest` command runs all tests successfully

---

## Phase 7: Deployment (P2)

### Task 7.1: Dockerfile
**Priority**: P2  
**Estimated**: 20 min  
**Dependencies**: Task 4.2

**Description**: Create minimal production Dockerfile.

**Acceptance Criteria**:
- [ ] `Dockerfile` with Python 3.11-slim base
- [ ] Copies `getback/` and `clients/` directories
- [ ] Sets working directory
- [ ] Exposes ports 9091 and 9092
- [ ] CMD runs `python -m getback`
- [ ] Manual test: `docker build` succeeds
- [ ] Manual test: `docker run -p 9091:9091 -p 9092:9092 getback` works

**Implementation**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY getback/ getback/
COPY clients/ clients/

EXPOSE 9091 9092

CMD ["python", "-m", "getback"]
```

---

### Task 7.2: Verify Kubernetes Deployment
**Priority**: P2  
**Estimated**: 30 min  
**Dependencies**: Task 7.1

**Description**: Test Skaffold deployment.

**Acceptance Criteria**:
- [ ] `skaffold dev` builds and deploys successfully
- [ ] 3 pods running
- [ ] Health probes passing
- [ ] Port forwarding works (curl localhost:9091)
- [ ] Manual test: 9 HTTP requests show round-robin pattern (1,1,1,2,2,2,3,3,3)
- [ ] Manual test: `/health` returns OK

---

## Summary

**Total Estimated Time**: ~10-12 hours

**Critical Path** (must complete in order):
1. Task 1.1 → 1.2, 1.3 → 1.4 → 4.2 (main application working)
2. Task 2.1, 2.2 → 2.3 (HTTP server)
3. Task 3.1 → 3.2 (TCP server)
4. Task 6.1, 6.2 (testing)

**Can be done in parallel**:
- Phase 5 (clients) can start after Phase 2/3
- Phase 7 (deployment) can start after Phase 4
- Tests (6.1) can be written alongside implementation

**Current Status**: Ready to implement  
**Next Step**: Start with Task 1.1 (Project Structure Setup)
