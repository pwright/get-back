# TCP Protocol Contract

**Version**: 1.0
**Protocol**: Custom text-based protocol over TCP
**Port**: 9092 (configurable)

## Overview

Command-based TCP protocol where client controls connection lifetime. Designed to demonstrate different load balancing behaviors (short-lived, timed, and persistent connections).

## Protocol Format

**Text-Based, Newline-Delimited**:
- All messages are UTF-8 text
- Commands terminated with `\n` (line feed)
- Responses terminated with `\n`

## Client Command Format

**Command Structure**: `{command}\n`

Three command types:

### 1. Numeric Command (Timed Connection)

**Format**: `{integer}\n`

**Examples**:
- `5\n` - Stay open for 5 seconds
- `1\n` - Stay open for 1 second
- `30\n` - Stay open for 30 seconds

**Behavior**:
- Server responds with counter
- Server sleeps for N seconds
- Server closes connection

**Invalid Numbers**:
- Non-integers (e.g., `"5.5\n"`, `"abc\n"`): Treated as arbitrary text (immediate close)
- Negative numbers: Treated as arbitrary text (immediate close)
- Zero (`"0\n"`): Immediate close (same as arbitrary)

### 2. OPEN Command (Persistent Connection)

**Format**: `OPEN\n`

**Behavior**:
- Server responds with counter
- Connection stays open indefinitely
- Client must close or server shutdown to terminate
- Multiple requests not supported (protocol is one command per connection)

**Use Case**: Testing persistent connection load balancing strategies

### 3. Arbitrary Text (Immediate Close)

**Format**: `{any_text}\n`

**Examples**:
- `hello\n`
- `test\n`
- `\n` (empty line)
- `random123\n`

**Behavior**:
- Server responds with counter
- Server closes connection immediately

## Server Response Format

**Response**: `{counter}\n`

**Example**:
```
42\n
```

**Timing**: Response sent immediately after command received, before honoring timing directive

## Full Protocol Exchange Examples

### Example 1: Timed Connection (5 seconds)

```
Client → Server: 5\n
Server → Client: 1\n
[5 second delay]
Server closes connection
```

**Timeline**:
- T+0ms: Connection established
- T+10ms: Client sends "5\n"
- T+12ms: Server responds "1\n"
- T+5012ms: Server closes connection

### Example 2: Persistent Connection

```
Client → Server: OPEN\n
Server → Client: 2\n
[connection stays open]
... (hours later)
Client closes or server shutdown
```

### Example 3: Immediate Close

```
Client → Server: hello\n
Server → Client: 3\n
Server closes connection immediately
```

**Timeline**:
- T+0ms: Connection established
- T+10ms: Client sends "hello\n"
- T+12ms: Server responds "3\n"
- T+13ms: Server closes connection

### Example 4: Empty Command

```
Client → Server: \n
Server → Client: 4\n
Server closes connection
```

## Counter Behavior

- TCP counter is independent of HTTP counter
- Starts at 1 on server startup
- Increments atomically for each connection
- Each connection gets unique value (no duplicates)
- No maximum value (wraps at integer limit, not expected in practice)

## Connection Lifecycle

### State Machine

```
CLOSED → ACCEPTING → CONNECTED → READING → RESPONDING → TIMING → CLOSED
                                                              ↓
                                                          PERSISTENT
```

**States**:
1. **CLOSED**: No connection
2. **ACCEPTING**: Server accepts TCP connection
3. **CONNECTED**: TCP handshake complete
4. **READING**: Server reads command (until `\n`)
5. **RESPONDING**: Server increments counter and sends response
6. **TIMING**: Honoring timing directive (sleep N seconds or immediate close)
7. **PERSISTENT**: OPEN command - stays in this state until explicit close
8. **CLOSED**: Connection terminated

### Timeout Behavior

**Read Timeout**: If client connects but sends no data:
- 30 second timeout (TCP keepalive default)
- Server logs timeout and closes connection
- Counter not incremented (no valid command received)

**Write Timeout**: If server cannot send response:
- Connection considered broken
- Close immediately
- Counter already incremented (committed)

## Client Implementation Notes

### Minimal Python Client

```python
import socket

def tcp_counter(host, port, command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(f"{command}\n".encode('utf-8'))
        response = sock.recv(1024).decode('utf-8').strip()
        return int(response)

# Examples
counter = tcp_counter('localhost', 9092, '5')  # 5 second connection
counter = tcp_counter('localhost', 9092, 'OPEN')  # persistent
counter = tcp_counter('localhost', 9092, 'hello')  # immediate
```

### With Timing Observation

```python
import socket
import time

def tcp_counter_timed(host, port, command):
    start = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(f"{command}\n".encode('utf-8'))
        response = sock.recv(1024).decode('utf-8').strip()
        # Connection closes here (with statement exit)
        duration = time.time() - start
    return int(response), duration

counter, duration = tcp_counter_timed('localhost', 9092, '3')
print(f"Counter: {counter}, Duration: {duration:.2f}s")
# Expected: Counter: 1, Duration: 3.0xs
```

### Persistent Connection Client

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 9092))
sock.sendall(b"OPEN\n")
response = sock.recv(1024).decode('utf-8').strip()
print(f"Counter: {response}, connection persistent")

# Connection stays open
# Do other work...

# Later: explicit close
sock.close()
```

## Load Balancer Testing Scenarios

### Scenario 1: Short-Lived Connections (Immediate Close)

```bash
# 10 rapid requests with immediate close
for i in {1..10}; do
  echo "request" | nc localhost 9092
done
```

**Expected**: Each request gets sequential counter (1, 2, 3, ..., 10)

**Load Balancer Behavior**: Round-robin or random works well (no persistent state)

### Scenario 2: Timed Connections (Demonstrate Connection Reuse)

```bash
# 3 concurrent 10-second connections
(echo "10" | nc localhost 9092 &)
(echo "10" | nc localhost 9092 &)
(echo "10" | nc localhost 9092 &)
```

**Expected**: 
- Three connections active simultaneously for 10 seconds
- Counters: 1, 2, 3
- All close after ~10 seconds

**Load Balancer Behavior**: 
- Least connections: Should distribute evenly while connections active
- Round-robin: May send new requests to busy backend if connections still open

### Scenario 3: Persistent Connections (OPEN Command)

```bash
# Open 3 persistent connections
(echo "OPEN" | nc localhost 9092) &
(echo "OPEN" | nc localhost 9092) &
(echo "OPEN" | nc localhost 9092) &

# New requests should go to least-loaded backend
echo "test" | nc localhost 9092
```

**Expected**:
- Three OPEN connections persist
- Fourth request gets routed based on LB strategy
- Least connections: Routes to backend with fewest OPEN connections

## Error Conditions

### Client-Side Errors

**Connection Refused**:
```
$ echo "test" | nc localhost 9092
Connection refused
```
- Server not running or port incorrect

**Connection Reset**:
- Server crashes during request
- Client sees: `Connection reset by peer`

**Timeout**:
- Client connects but server doesn't respond within timeout
- Use `nc -w5` for 5 second timeout

### Server-Side Errors

**Invalid Command Parsing**:
- Non-UTF-8 data: Close connection, log error
- Binary data: Close connection, log warning

**Multiple Commands on Same Connection**:
- Protocol: One command per connection
- Server ignores data after first `\n`
- Connection timing based on first command only

**Resource Exhaustion**:
- Too many OPEN connections: OS-level limit
- Server continues accepting, may refuse new connections
- Logged as warning

## Performance Characteristics

**Latency**:
- <10ms for local connections (localhost)
- <100ms for LAN connections
- Timing precision: ±50ms for timed connections (asyncio.sleep granularity)

**Throughput**:
- 100+ connections/sec for immediate close
- Limited by connection setup overhead, not counter logic

**Concurrent Connections**:
- Designed for hundreds of concurrent connections
- OPEN connections consume ~1KB memory each
- No artificial limit (OS limits apply)

**Connection Duration Accuracy**:
- Timed connections: Server sleeps for N seconds ±50ms
- Measured from response sent to connection close
- OPEN connections: No timeout, stays open until close signal

## Concurrency & Thread Safety

**Multiple Clients**:
- Counter increments are atomic (no race conditions)
- Each client gets unique counter value
- Order determined by arrival time (TCP accept order)

**No Request Pipelining**:
- Protocol: One command per connection
- Multiple requests require multiple connections

## Security Considerations

**Not Production-Ready**:
- No authentication
- No encryption (plain TCP)
- No rate limiting
- Resource exhaustion possible (many OPEN connections)
- Binds to 0.0.0.0 by default (all interfaces)

**Intended Use**: Demonstration and testing only

## Logging

**Events Logged** (INFO level):
- Server startup: `TCP server listening on {host}:{port}`
- Connection accepted: `TCP connection from {remote_addr}`
- Command received: `TCP command from {remote_addr}: {command}`
- Counter incremented: `TCP counter: {value}`
- Connection mode: `TCP connection mode: {timed|persistent|immediate}`
- Connection closed: `TCP connection closed: {remote_addr}, duration: {seconds}s`

**Debug Level**:
- Raw data received
- Timing sleep start/end
- Active connection set changes (OPEN command tracking)

## Protocol Versioning

**Version**: 1.0 (initial)

**Future Compatibility**:
- Protocol designed for extension
- Could add commands: `CLOSE`, `STATUS`, `RESET`
- Current behavior: Unknown commands treated as arbitrary text (immediate close)

**Client Compatibility**:
- Clients should send exactly one command per connection
- Clients can detect timed vs immediate close by measuring connection duration
- OPEN detection: Connection stays open after response
