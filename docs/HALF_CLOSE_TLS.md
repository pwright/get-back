# TLS Half-Close Support

This document explains how to test TCP half-close over TLS connections using the Go client.

## The Problem

Python's `ssl` module **cannot perform half-close operations** over TLS:

```python
# This works for plain TCP
writer.write_eof()  # ✓ Sends FIN

# This FAILS for TLS
ssl_writer.write_eof()  # ✗ Doesn't work correctly
```

**Why**: TLS requires sending a `close_notify` alert before the TCP FIN. Python's SSL wrapper doesn't expose this as a half-close primitive.

## The Solution: Go Client

Go's `crypto/tls` package provides `tls.Conn.CloseWrite()`:

```go
// Sends close_notify alert + FIN, keeps reading
tlsConn.CloseWrite()  // ✓ Proper TLS half-close
```

## Quick Start

### 1. Build the Go Client

```bash
cd clients
make build
# Or manually:
# go build -o halfclose_client halfclose_client.go
```

### 2. Test with TLS

```bash
# Self-signed certificate (skip verification)
./halfclose_client -host localhost -port 9092 -tls -insecure

# Proper certificate
./halfclose_client -host getback.example.com -port 9092 -tls
```

## Use Cases

### Use Case 1: Skupper with TLS Backend

**Setup**: Get-back server with TLS, exposed via skupper

```bash
# Terminal 1: Start server with TLS
python -m getback --tcp-tls

# Terminal 2: Expose via skupper
skupper expose deployment/getback --port 9092 --protocol tcp

# Terminal 3: Test TLS half-close through skupper
./halfclose_client -host skupper-listener -port 9092 -tls -insecure
```

**What this tests**:
- Skupper correctly forwards TLS `close_notify` alerts
- Skupper maintains TCP half-close semantics through TLS
- Backend server correctly handles TLS half-close

### Use Case 2: Multi-Cluster with TLS

**Setup**: Backend in cluster A, client in cluster B, skupper link between

```yaml
# Cluster A: Backend with TLS
apiVersion: apps/v1
kind: Deployment
metadata:
  name: getback
spec:
  template:
    spec:
      containers:
      - name: getback
        env:
        - name: GETBACK_TCP_TLS
          value: "true"
        - name: TLS_CERT_PATH
          value: "/etc/tls/cert.pem"
        - name: TLS_KEY_PATH
          value: "/etc/tls/key.pem"
```

```bash
# Cluster B: Test pod
kubectl run go-test --image=golang:1.22 --restart=Never -- sleep infinity
kubectl cp halfclose_client go-test:/tmp/
kubectl exec -it go-test -- /tmp/halfclose_client \
  -host getback.cluster-a -port 9092 -tls -insecure
```

### Use Case 3: Load Balancer with TLS Passthrough

**Setup**: HAProxy or skupper doing TLS passthrough

```bash
# HAProxy config (TLS passthrough mode)
frontend tcp-frontend
    mode tcp
    bind *:9092
    default_backend tcp-backend

backend tcp-backend
    mode tcp
    balance roundrobin
    server backend1 10.0.1.10:9092
    server backend2 10.0.1.11:9092

# Test TLS half-close through load balancer
./halfclose_client -host haproxy -port 9092 -tls -insecure
```

## TLS Half-Close Protocol

### HALF_CLOSE_SEND (Server sends FIN first)

```
Client                         Server
  |--ClientHello--------------->|
  |<-ServerHello----------------|
  |  ... TLS handshake ...      |
  |--"HALF_CLOSE_SEND\n"------->|
  |<-{counter:1}-----------------|
  |<-close_notify alert---------|  (TLS shutdown write)
  |<-FIN------------------------|  (TCP half-close)
  |--ACK----------------------->|
  |--"some data\n"------------->|  (client can still send)
  |--close_notify alert-------->|  (client TLS shutdown)
  |--FIN----------------------->|  (client TCP close)
  |<-ACK------------------------|
  |  Connection fully closed    |
```

### HALF_CLOSE_READ (Client sends FIN first)

```
Client                         Server
  |--ClientHello--------------->|
  |<-ServerHello----------------|
  |  ... TLS handshake ...      |
  |--"HALF_CLOSE_READ\n"------->|
  |<-{counter:1}-----------------|
  |--"test data 1\n"----------->|
  |--"test data 2\n"----------->|
  |--close_notify alert-------->|  (client TLS shutdown write)
  |--FIN----------------------->|  (client TCP half-close)
  |                              |  (server reads until EOF)
  |<-close_notify alert---------|  (server TLS shutdown)
  |<-FIN------------------------|  (server TCP close)
  |--ACK----------------------->|
  |  Connection fully closed    |
```

## Command Line Options

```bash
./halfclose_client [flags]

Flags:
  -host string      Server hostname or IP (default "localhost")
  -port string      Server port (default "9092")
  -mode string      Test mode: send, read, or both (default "both")
  -tls              Enable TLS encryption
  -insecure         Skip TLS certificate verification (for self-signed certs)
```

### Examples

```bash
# Plain TCP (no TLS)
./halfclose_client -host localhost -port 9092

# TLS with self-signed certificate
./halfclose_client -host localhost -port 9092 -tls -insecure

# TLS with proper certificate
./halfclose_client -host getback.prod.example.com -port 9092 -tls

# Only test server-initiated FIN
./halfclose_client -host localhost -port 9092 -tls -insecure -mode send

# Only test client-initiated FIN
./halfclose_client -host localhost -port 9092 -tls -insecure -mode read
```

## Comparison: Python vs Go

| Feature | Python Client | Go Client |
|---------|---------------|-----------|
| **Plain TCP half-close** | ✅ Works | ✅ Works |
| **TLS half-close** | ❌ Fails | ✅ Works |
| **Dependencies** | Python 3.6+ | None (static binary) |
| **Build required** | No | Yes (once) |
| **Dashboard integration** | ✅ Yes | ❌ No (CLI only) |
| **Cross-platform** | ✅ (if Python installed) | ✅ (compile for target) |
| **Container-friendly** | Moderate | ✅ (single binary) |

## Building for Different Platforms

```bash
# Current platform
make build

# All platforms
make build-all

# Specific platforms
make build-linux
make build-macos
make build-windows

# Clean
make clean
```

Or manually:

```bash
# Linux
GOOS=linux GOARCH=amd64 go build -o halfclose_client.linux halfclose_client.go

# macOS
GOOS=darwin GOARCH=amd64 go build -o halfclose_client.macos halfclose_client.go

# Windows
GOOS=windows GOARCH=amd64 go build -o halfclose_client.exe halfclose_client.go
```

## Troubleshooting

### "TLS handshake failure"

```
Error: connect failed: tls: handshake failure
```

**Causes**:
1. Server doesn't have TLS enabled
2. Port is for plain TCP, not TLS
3. TLS configuration mismatch

**Solutions**:
1. Verify server has `--tcp-tls` or `GETBACK_TCP_TLS=true`
2. Check you're connecting to TLS port (not plain TCP port)
3. Use `-insecure` for self-signed certificates

### "x509: certificate signed by unknown authority"

```
Error: x509: certificate signed by unknown authority
```

**Cause**: Server using self-signed certificate without `-insecure` flag.

**Solution**: Add `-insecure` flag for testing:

```bash
./halfclose_client -host localhost -port 9092 -tls -insecure
```

For production, use proper CA-signed certificates.

### "Connection refused"

```
Error: connect failed: dial tcp: connection refused
```

**Causes**:
1. Server not running
2. Wrong port
3. Firewall blocking connection

**Solutions**:
1. Start server: `python -m getback --tcp-tls`
2. Verify port matches server configuration
3. Check firewall rules

### Unexpected EOF during half-close

```
Error: read response failed: EOF
```

**Causes**:
1. Skupper converting FIN to RST
2. Server error during half-close
3. Network issue

**Debug**:
1. Test locally without skupper to isolate issue
2. Check server logs for errors
3. Use tcpdump to observe FIN vs RST packets:

```bash
sudo tcpdump -i any -nn 'tcp port 9092' -X
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test TLS Half-Close

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Go
      uses: actions/setup-go@v4
      with:
        go-version: '1.22'
    
    - name: Build Go client
      run: |
        cd clients
        go build -o halfclose_client halfclose_client.go
    
    - name: Start get-back server
      run: |
        pip install -e .
        python -m getback --tcp-tls &
        sleep 2
    
    - name: Test TLS half-close
      run: |
        cd clients
        ./halfclose_client -host localhost -port 9092 -tls -insecure
```

## Security Considerations

### Using `-insecure` Flag

The `-insecure` flag skips TLS certificate verification. Use it **only** for:
- Testing with self-signed certificates
- Development/staging environments
- Internal skupper clusters without PKI

**Never use in production** with external or untrusted endpoints.

### Proper Certificate Verification

For production, use proper CA-signed certificates:

```bash
# Production: Verifies certificate chain
./halfclose_client -host getback.prod.example.com -port 9092 -tls

# This will fail if:
# - Certificate is self-signed
# - Certificate is expired
# - Hostname doesn't match certificate
# - CA is not in system trust store
```

## Performance Notes

TLS half-close adds minimal overhead:
- `close_notify` alert: ~100 bytes
- CPU: negligible (single encryption operation)
- Latency: <1ms typically

The Go client maintains the same performance characteristics as plain TCP half-close.

## References

- Go `crypto/tls` package: https://pkg.go.dev/crypto/tls
- `tls.Conn.CloseWrite()`: https://pkg.go.dev/crypto/tls#Conn.CloseWrite
- TLS close_notify: RFC 5246 Section 7.2.1
- TCP half-close: RFC 793 Section 3.5
- Skupper TCP routing: https://skupper.io/docs/
