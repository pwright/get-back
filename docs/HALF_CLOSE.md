# Half-Close TCP Testing

This document explains the half-close testing feature added to get-back for testing skupper router behavior with TCP half-closed connections.

## What is TCP Half-Close?

TCP is a full-duplex protocol, meaning data can flow in both directions simultaneously. A "half-close" occurs when one side of the connection closes its write side (sends a FIN packet) while keeping the read side open.

This is different from a full close where both sides are shut down simultaneously.

### Why Test Half-Close?

Network proxies and routers (like skupper) must correctly handle FIN packets to maintain TCP semantics. Common failure modes include:
- Converting FIN to RST (reset), causing connection abortion
- Dropping FIN packets, causing connections to hang
- Not properly signaling EOF to the other side

## Half-Close Commands

Get-back implements two half-close test scenarios:

### HALF_CLOSE_SEND

**Server behavior**:
1. Receives command from client
2. Sends counter response immediately
3. Calls `write_eof()` (Python asyncio) or `shutdown(SHUT_WR)` (raw sockets)
   - This sends a TCP FIN packet on the write side
   - Server enters FIN_WAIT_1 state
4. Keeps reading from client until client closes

**Use case**: Tests if skupper correctly forwards server-initiated FIN packets and allows continued data flow from client to server.

**Expected behavior**:
- Client receives response
- Client receives EOF (empty read) indicating server closed write side
- Client can still send data to server
- Connection fully closes when client sends FIN

### HALF_CLOSE_READ

**Server behavior**:
1. Receives command from client
2. Sends counter response immediately
3. Reads from client until EOF (client's FIN)
4. Closes connection normally

**Use case**: Tests if skupper correctly detects and signals client-initiated FIN packets to the server.

**Expected behavior**:
- Server receives command
- Server sends response
- Server continues reading
- Client sends FIN (shutdown write side)
- Server detects EOF
- Connection fully closes

## Implementation Details

### Server (tcp_server.py)

```python
# HALF_CLOSE_SEND
writer.write_eof()  # Send FIN on write side
await writer.drain()
# Keep reading until client closes
while True:
    data = await reader.read(1024)
    if not data:  # Client sent FIN
        break

# HALF_CLOSE_READ
# Read until client sends FIN
while True:
    data = await reader.read(1024)
    if not data:  # Client sent FIN
        break
# Response was already sent, now close normally
```

### Dashboard GUI

Two new buttons in the TCP section:
- **HC Send**: Sends `HALF_CLOSE_SEND` command to Amount backends concurrently
- **HC Read**: Sends `HALF_CLOSE_READ` command to Amount backends concurrently

### Python Client (halfclose_client.py)

Standalone test client for manual verification:

```bash
# Test both modes
python clients/halfclose_client.py localhost 9092

# Test only server-initiated FIN
python clients/halfclose_client.py skupper-listener 9092 send

# Test only client-initiated FIN
python clients/halfclose_client.py skupper-listener 9092 read
```

## Testing with Skupper

### Scenario 1: Local Baseline

First verify half-close works correctly without skupper:

```bash
# Terminal 1: Start get-back server
python -m getback

# Terminal 2: Test half-close
python clients/halfclose_client.py localhost 9092
```

**Expected**: Both tests pass with clean EOF signals.

### Scenario 2: Skupper Single-Cluster

Test half-close through skupper listener in the same cluster:

```bash
# Terminal 1: Create skupper listener
skupper expose deployment/getback --port 9092 --protocol tcp

# Terminal 2: Test through skupper
python clients/halfclose_client.py skupper-listener 9092
```

**Expected**: Both tests pass. If skupper drops FIN:
- HALF_CLOSE_SEND: Client never receives EOF, connection hangs
- HALF_CLOSE_READ: Server never detects client FIN, connection hangs

### Scenario 3: Skupper Multi-Cluster

Test half-close across skupper link between clusters:

```bash
# Cluster A: Backend
kubectl apply -f k8s/getback-deployment.yaml

# Cluster B: Client pod
kubectl run test-client --image=python:3.13 --restart=Never -- sleep infinity
kubectl exec -it test-client -- bash

# Inside test-client pod
apt-get update && apt-get install -y git
git clone <repo-url>
cd get-back
python clients/halfclose_client.py getback.cluster-a 9092
```

**Expected**: Both tests pass across the skupper link.

## Observing Half-Close Behavior

### Server Logs

With `--log-level DEBUG`:

```
INFO:getback.tcp_server:TCP connection from ('127.0.0.1', 54321)
INFO:getback.tcp_server:TCP command from ('127.0.0.1', 54321): HALF_CLOSE_SEND
INFO:getback.tcp_server:TCP counter: 1 (server: hostname-abc, mode: half_close_send)
INFO:getback.tcp_server:TCP half-close (send): shutting down write side for ('127.0.0.1', 54321)
INFO:getback.tcp_server:TCP half-close (send): received EOF from client ('127.0.0.1', 54321)
DEBUG:getback.tcp_server:TCP connection closed: ('127.0.0.1', 54321)
```

### Client Output

```
=== Test: HALF_CLOSE_SEND ===
✓ Connected to localhost:9092
✓ Sent command: HALF_CLOSE_SEND
✓ Received response: {"counter":1,"server":"...","timestamp":...}
✓ Received EOF from server (server closed write side)
✓ Sending some data to server...
✓ Closed our write side (sent FIN)
✓ Test complete in 0.12s
✓ Server handled half-close correctly
```

### Network Capture

Using tcpdump to observe FIN packets:

```bash
# Terminal 1: Capture TCP traffic
sudo tcpdump -i lo -nn 'tcp port 9092' -X

# Terminal 2: Run half-close test
python clients/halfclose_client.py localhost 9092 send
```

**Look for**:
- FIN flag from server after response
- ACK from client
- Data from client to server (after server FIN)
- FIN flag from client
- ACK from server
- Final connection teardown

## Python vs Go for TLS Half-Close

### Python Client (`halfclose_client.py`)

**Supports**: Plain TCP only

**Limitation**: Python's `ssl` module wraps sockets in an `SSLSocket` that doesn't support half-close. The `write_eof()` method or `shutdown(SHUT_WR)` on an SSL connection will fail or behave incorrectly because:
- TLS requires sending a `close_notify` alert before the FIN
- Python's SSL implementation doesn't expose this primitive
- The SSL wrapper prevents direct socket manipulation

**When to use**: Testing plain TCP half-close (no TLS) locally or through skupper without TLS.

```bash
python clients/halfclose_client.py localhost 9092
```

### Go Client (`halfclose_client.go`)

**Supports**: Both plain TCP and TLS

**Advantage**: Go's `crypto/tls` package properly implements TLS half-close via `tls.Conn.CloseWrite()`:
- Sends proper TLS `close_notify` alert (RFC 5246)
- Sends TCP FIN packet
- Keeps read side open for receiving data
- Works exactly as expected for TLS connections

**When to use**: 
- Testing TLS half-close (required)
- Testing plain TCP half-close (works fine too)
- Distributing static binaries
- Container/Kubernetes environments

```bash
# Build once
cd clients
go build -o halfclose_client halfclose_client.go

# Use with TLS
./halfclose_client -host localhost -port 9092 -tls -insecure

# Use with plain TCP (same as Python)
./halfclose_client -host localhost -port 9092
```

See `clients/GO_CLIENT.md` for full documentation.

### Dashboard GUI

The dashboard "HC Send" and "HC Read" buttons use the Python asyncio client internally, so they:
- ✅ Work with plain TCP
- ❌ Do not support TLS half-close

For TLS half-close testing, use the Go client from the command line.

## Common Issues

### Connection Hangs

**Symptom**: Client waits indefinitely, never receives EOF.

**Likely cause**: Skupper is dropping FIN packets or converting them to RST.

**Debug**:
1. Test locally (no skupper) to verify baseline
2. Run tcpdump on both client and server to see if FIN is sent/received
3. Check skupper-router logs for TCP state machine errors

### Immediate Connection Reset

**Symptom**: Client receives `Connection reset by peer` instead of clean close.

**Likely cause**: Skupper is converting FIN to RST.

**Debug**: Network capture will show RST packet instead of FIN.

### Response Never Arrives

**Symptom**: Client connects but never receives counter response.

**Likely cause**: Server error or network issue (not half-close specific).

**Debug**: Check server logs, verify server is running.

## References

- TCP Half-Close: RFC 793 Section 3.5 (Closing a Connection)
- Python asyncio streams: [`StreamWriter.write_eof()`](https://docs.python.org/3/library/asyncio-stream.html#asyncio.StreamWriter.write_eof)
- Go TLS half-close: [`tls.Conn.CloseWrite()`](https://pkg.go.dev/crypto/tls#Conn.CloseWrite)
- Skupper router TCP handling: [skupper-router source](https://github.com/skupperproject/skupper-router)
