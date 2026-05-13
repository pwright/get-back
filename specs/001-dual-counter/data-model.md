# Data Model: Dual-Protocol Counter Service

**Phase**: 1 - Design
**Date**: 2026-05-13
**Feature**: Dual-Protocol Counter Service

## Overview

This service has minimal data entities - primarily runtime state (counters and active connections). No persistence, no complex relationships.

## Core Entities

### Counter

**Purpose**: Atomic integer that increments for each request

**Fields**:
- `_value`: int - Current counter value (private, accessed via methods)
- `_lock`: asyncio.Lock - Synchronization primitive for atomic increments

**Behavior**:
- Initialized to 0 on server start
- `increment()` method atomically increments and returns new value
- Thread-safe via asyncio.Lock

**Lifecycle**:
- Created at server startup (two instances: HTTP counter, TCP counter)
- Exists in memory for server lifetime
- Reset on server restart (no persistence)

**Validation Rules**:
- Value must be non-negative integer
- Increment operation must be atomic (no race conditions)
- No maximum value enforced (assumes restart before integer overflow)

### HTTPServer

**Purpose**: Asyncio server accepting HTTP GET requests, returning counter values

**Fields**:
- `host`: str - Bind address (e.g., "0.0.0.0")
- `port`: int - HTTP listen port (default 9091)
- `counter`: Counter - Reference to HTTP counter instance
- `server`: asyncio.Server - Underlying asyncio server object

**Behavior**:
- Accepts TCP connections, parses HTTP request (any method/path)
- Special handling for `/health` path: Returns 200 OK without incrementing counter
- All other paths: Increments counter and returns value
- Responds with HTTP/1.0 format: `HTTP/1.0 200 OK\r\n\r\n{counter}\n` or `HTTP/1.0 200 OK\r\n\r\nOK\n` (health)
- Closes connection after response

**Lifecycle**:
- Created and started via `asyncio.start_server()` at application startup
- Runs until shutdown signal received
- Gracefully closes all active connections on shutdown

**State Transitions**:
```
STOPPED → STARTING → LISTENING → STOPPING → STOPPED
                         ↓
                   (accept connections)
```

### TCPServer

**Purpose**: Asyncio server accepting TCP connections with command-based protocol

**Fields**:
- `host`: str - Bind address
- `port`: int - TCP listen port (default 9092)
- `counter`: Counter - Reference to TCP counter instance
- `server`: asyncio.Server - Underlying asyncio server object
- `active_connections`: set - Set of open connections (for OPEN command tracking)

**Behavior**:
- Accepts connections, reads newline-delimited command
- Increments counter
- Responds with `{counter}\n`
- Honors timing directive:
  - Numeric (e.g., "5"): Sleep N seconds, then close
  - "OPEN": Add to active_connections, keep open indefinitely
  - Other: Close immediately

**Lifecycle**:
- Created and started via `asyncio.start_server()` at application startup
- Maintains set of persistent connections (OPEN commands)
- Cleanup active connections on shutdown

**State Transitions**:
```
STOPPED → STARTING → LISTENING → STOPPING → STOPPED
                         ↓
                   (per-connection state)
                   
Connection states:
ACCEPTED → READING_COMMAND → RESPONDING → WAITING/OPEN/CLOSING → CLOSED
```

### Configuration

**Purpose**: Server configuration from CLI args and environment variables

**Fields**:
- `http_port`: int - HTTP server port (default 9091)
- `tcp_port`: int - TCP server port (default 9092)
- `host`: str - Bind address (default "0.0.0.0")
- `log_level`: str - Logging level (default "INFO")

**Behavior**:
- Loaded at startup via argparse
- Environment variable fallback (e.g., HTTP_PORT)
- Immutable after startup

**Validation Rules**:
- Ports must be 1-65535
- Host must be valid IP or "0.0.0.0"
- Log level must be valid logging level (DEBUG, INFO, WARNING, ERROR)

## Relationships

```
Application
    ├─> HTTPServer
    │       └─> Counter (HTTP)
    ├─> TCPServer
    │       └─> Counter (TCP)
    └─> Configuration
```

**Key Points**:
- HTTP and TCP counters are independent (no shared state)
- Servers reference counters but don't own them (could be shared in future if needed)
- No database, no files, no external state - pure in-memory

## State Management

### Concurrent Access

**HTTP Counter**:
- Multiple concurrent HTTP requests may increment simultaneously
- asyncio.Lock ensures atomic increments
- No reader/writer distinction needed (increment-only)

**TCP Counter**:
- Multiple concurrent TCP connections may increment simultaneously
- Same asyncio.Lock protection as HTTP counter
- TCP server also manages active_connections set (OPEN commands)

### Connection Tracking

**HTTP**: Stateless - no connection tracking needed beyond asyncio server's internal handling

**TCP**: Stateful for OPEN commands
- `active_connections: Set[asyncio.StreamWriter]` tracks persistent connections
- Add when OPEN command received
- Remove on explicit close or error
- Iterate and close all on shutdown

## Error States

### Counter Errors
- **Concurrent increment failure**: Cannot occur (Lock protection)
- **Integer overflow**: Not handled (assumption: restart before overflow)

### Server Errors
- **Port already in use**: Caught at startup, log and exit with error code
- **Connection limit exceeded**: OS-level limit, log warning, accept when available
- **Client disconnect during request**: Log info, cleanup connection, continue serving

### TCP Protocol Errors
- **Invalid numeric command** (e.g., "abc", "5.5"): Treat as arbitrary (immediate close)
- **Malformed data**: Log warning, close connection
- **Timeout (no data)**: Close after 30s default keepalive
- **Client sends data after initial command**: Ignored (protocol is one command per connection)

## Data Flow

### HTTP Request Flow
```
1. Client connects to HTTP port
2. Server reads HTTP request (until \r\n\r\n)
3. Counter.increment() called (Lock acquired)
4. Response sent: HTTP/1.0 200 OK\r\n\r\n{counter}\n
5. Connection closed
6. Log event (protocol=HTTP, counter={value})
```

### TCP Request Flow
```
1. Client connects to TCP port
2. Server reads line (until \n)
3. Parse command:
   - If numeric and valid: duration = int(command)
   - If "OPEN": duration = None (indefinite)
   - Else: duration = 0 (immediate)
4. Counter.increment() called (Lock acquired)
5. Response sent: {counter}\n
6. Apply duration:
   - 0: Close immediately
   - N: await asyncio.sleep(N), then close
   - None: Add to active_connections, keep open
7. Log event (protocol=TCP, counter={value}, command={cmd}, duration={dur})
```

## Memory Considerations

**Per-Connection Memory**:
- HTTP: ~4KB (HTTP request buffer)
- TCP: ~1KB (single line buffer)

**Long-lived State**:
- Counters: 2 integers (~16 bytes each)
- Active connections set: ~8 bytes per OPEN connection
- Server objects: ~1KB each

**Expected Memory Footprint**: <10MB for server + reasonable connection count (<1000)

**No Memory Leaks**: All connections cleaned up on close, no circular references

## Validation Summary

All entities follow constitution principles:
- **Simple**: Minimal fields, clear responsibilities
- **Clear boundaries**: Counter separate from servers, servers separate from each other
- **Observable**: All state changes logged
- **Testable**: Each entity independently testable via mocking/fixtures
