# Go Half-Close Client

Go client for testing TCP half-close with **TLS support**. Use this when you need to test half-close behavior over TLS connections, as Python's `ssl` module doesn't support TLS half-close.

## Why Go?

- ✅ **TLS half-close support**: Go's `tls.Conn.CloseWrite()` sends proper TLS `close_notify` alert + FIN
- ✅ **Works with plain TCP too**: Single client handles both TCP and TLS
- ✅ **No dependencies**: Uses only Go standard library
- ✅ **Cross-platform**: Compiles to static binary for Linux, macOS, Windows

## Building

```bash
# Build for current platform
cd clients
go build -o halfclose_client halfclose_client.go

# Build for Linux (from macOS/Windows)
GOOS=linux GOARCH=amd64 go build -o halfclose_client.linux halfclose_client.go

# Build for macOS (from Linux/Windows)
GOOS=darwin GOARCH=amd64 go build -o halfclose_client.macos halfclose_client.go

# Build for Windows (from Linux/macOS)
GOOS=windows GOARCH=amd64 go build -o halfclose_client.exe halfclose_client.go
```

## Usage

```bash
./halfclose_client [flags]

Flags:
  -host string      Server host (default "localhost")
  -port string      Server port (default "9092")
  -mode string      Test mode: send, read, or both (default "both")
  -tls              Use TLS encryption
  -insecure         Skip TLS certificate verification (for self-signed certs)
```

## Examples

### Plain TCP (same as Python client)

```bash
# Test both modes on plain TCP
./halfclose_client -host localhost -port 9092

# Test only server-initiated FIN
./halfclose_client -host localhost -port 9092 -mode send

# Test only client-initiated FIN
./halfclose_client -host localhost -port 9092 -mode read
```

### TLS (the reason to use Go)

```bash
# Test both modes over TLS with proper certificate
./halfclose_client -host getback.example.com -port 9092 -tls

# Test with self-signed certificate (skip verification)
./halfclose_client -host localhost -port 9092 -tls -insecure

# Test through skupper with TLS
./halfclose_client -host skupper-listener -port 9092 -tls -insecure
```

## Output Example

```
Half-Close TCP Client (Go)
Target: localhost:9092
TLS: true
Mode: both

=== Test: HALF_CLOSE_SEND ===
Server will send response, shutdown write side (send FIN), then keep reading
✓ Connected to localhost:9092
✓ Sent command: HALF_CLOSE_SEND
✓ Received response: {"counter":1,"server":"hostname-abc","timestamp":1234567890}
✓ Received EOF from server (server closed write side)
✓ Sending some data to server...
✓ Sent TLS close_notify and closed our write side (sent FIN)
✓ Test complete in 0.15s
✓ Server handled half-close correctly

=== Test: HALF_CLOSE_READ ===
Server will read until client FIN, then send response
✓ Connected to localhost:9092
✓ Sent command: HALF_CLOSE_READ
✓ Received initial response: {"counter":2,"server":"hostname-abc","timestamp":1234567890}
✓ Sending some data to server...
✓ Sent TLS close_notify and closed our write side (sent FIN)
✓ Received EOF from server (server closed connection)
✓ Test complete in 0.12s
✓ Server handled half-close correctly

✓ All tests passed!
```

## TLS Half-Close Details

When using `-tls`, the Go client performs proper TLS half-close:

1. **CloseWrite() behavior**:
   - Sends TLS `close_notify` alert (RFC 5246)
   - Sends TCP FIN packet
   - Keeps read side open
   - Read side can still receive data until server closes

2. **TLS alert sequence**:
   ```
   Client                           Server
     |--close_notify alert--------->|
     |--FIN------------------------>|
     |                               |  (server can still send)
     |<-close_notify alert----------|
     |<-FIN--------------------------|
     |--ACK------------------------->|
   ```

This is **not possible** with Python's `ssl` module, which doesn't expose a half-close primitive for TLS connections.

## Comparison: Go vs Python

| Feature | Python Client | Go Client |
|---------|---------------|-----------|
| Plain TCP half-close | ✅ | ✅ |
| TLS half-close | ❌ | ✅ |
| Dependencies | Python 3.6+ | Go 1.16+ (build only) |
| Runtime | Python interpreter | Static binary |
| Distribution | Source code | Single executable |

## Testing Scenarios

### Scenario 1: Local TLS Server

```bash
# Terminal 1: Start get-back with TLS
python -m getback --tcp-tls

# Terminal 2: Test TLS half-close
./halfclose_client -host localhost -port 9092 -tls -insecure
```

### Scenario 2: Skupper with TLS

```bash
# Skupper listener with TLS backend
skupper expose deployment/getback --port 9092 --protocol tcp

# Test through skupper with TLS
./halfclose_client -host skupper-listener -port 9092 -tls -insecure
```

### Scenario 3: Multi-Cluster Skupper with TLS

```bash
# From a pod in cluster B (with skupper link to cluster A)
kubectl run go-test --image=golang:1.22 --restart=Never -- sleep infinity
kubectl cp halfclose_client go-test:/tmp/
kubectl exec -it go-test -- /tmp/halfclose_client \
  -host getback.cluster-a -port 9092 -tls -insecure
```

## Troubleshooting

### TLS Handshake Failed

```
Error: connect failed: tls: handshake failure
```

**Cause**: Server doesn't have TLS enabled or certificate issue.

**Fix**: 
- Verify server is running with `--tcp-tls`
- Use `-insecure` flag for self-signed certificates
- Check server TLS configuration

### Certificate Verification Failed

```
Error: x509: certificate signed by unknown authority
```

**Cause**: Server using self-signed certificate.

**Fix**: Use `-insecure` flag for testing, or add proper CA certificate.

### Connection Refused

```
Error: connect failed: dial tcp: connection refused
```

**Cause**: Server not running or wrong port.

**Fix**: Check server is running on specified port.

## Building for Container Images

To include in a Docker image:

```dockerfile
# Multi-stage build
FROM golang:1.22 AS builder
WORKDIR /build
COPY clients/halfclose_client.go .
RUN go build -o halfclose_client halfclose_client.go

FROM alpine:latest
COPY --from=builder /build/halfclose_client /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/halfclose_client"]
```

Build and run:

```bash
docker build -t halfclose-client -f Dockerfile.client .
docker run --rm halfclose-client -host getback -port 9092 -tls -insecure
```

## Development

The Go client is a standalone program with no external dependencies:

```go
import (
    "bufio"
    "crypto/tls"
    "flag"
    "fmt"
    "io"
    "net"
    "os"
    "strings"
    "time"
)
```

Key functions:
- `testHalfCloseSend()`: Tests server-initiated FIN
- `testHalfCloseRead()`: Tests client-initiated FIN  
- `connect()`: Creates TCP or TLS connection
- `tls.Conn.CloseWrite()`: The magic that Python can't do

## When to Use Which Client

**Use Python client** (`halfclose_client.py`):
- Testing plain TCP without TLS
- When Python is already available
- Quick local verification

**Use Go client** (`halfclose_client`):
- Testing TLS half-close (required)
- Building static binaries for distribution
- Container/Kubernetes environments
- Cross-platform testing

## References

- Go TLS package: https://pkg.go.dev/crypto/tls
- `CloseWrite()` docs: https://pkg.go.dev/crypto/tls#Conn.CloseWrite
- TLS close_notify: RFC 5246 Section 7.2.1
- TCP half-close: RFC 793 Section 3.5
