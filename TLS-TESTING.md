# TLS Testing Guide

This document explains how to test the native Python TLS/SSL implementation.

## Local Testing with Self-Signed Certificates

### 1. Generate Test Certificates

```bash
# Generate self-signed cert (valid 365 days)
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/test-key.pem \
  -out /tmp/test-cert.pem \
  -days 365 \
  -subj "/CN=localhost"
```

### 2. Start TLS-Enabled Server

```bash
# Using environment variables
TLS_CERT_PATH=/tmp/test-cert.pem \
TLS_KEY_PATH=/tmp/test-key.pem \
python -m getback --host 127.0.0.1

# Or using CLI arguments
python -m getback \
  --host 127.0.0.1 \
  --tls-cert /tmp/test-cert.pem \
  --tls-key /tmp/test-key.pem
```

Expected output:
```
Starting Get-Back (TLS enabled) | HTTP:9091 TCP:9092 Dashboard:9093
✓ HTTPS ready on 127.0.0.1:9091
✓ TLS-TCP ready on 127.0.0.1:9092
✓ Dashboard ready at https://127.0.0.1:9093/
```

### 3. Test HTTPS Endpoint

```bash
# Test with curl (self-signed cert, so -k to skip verification)
curl -k https://localhost:9091/

# Expected response (JSON):
{"counter":1,"server":"your-hostname","timestamp":1234567890}
```

### 4. Test TLS-TCP Endpoint

```bash
# Using openssl s_client
echo "test" | openssl s_client -connect localhost:9092 -quiet 2>/dev/null

# Expected response (JSON):
{"counter":1,"server":"your-hostname","timestamp":1234567890}
```

### 5. Test Dashboard with TLS

```bash
# Access dashboard in browser
# Accept the self-signed certificate warning
open https://localhost:9093/

# Configure to test TLS backend:
# Backend: localhost:9091
# Check "Use HTTPS" checkbox
# Click "Send HTTP Request"
```

## Kubernetes Testing

### 1. Deploy Plain Backend (no TLS)

```bash
kubectl apply -f east/deployment.yaml
kubectl apply -f east/service.yaml
```

### 2. Deploy TLS Backend

```bash
# Run automated script (handles cert generation)
cd east
./deploy-tls-backend.sh

# Or manually:
# 1. Generate cert
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout /tmp/key.pem -out /tmp/cert.pem -days 365 \
  -subj "/CN=getback-tls"

# 2. Create secret
kubectl create secret generic getback-tls-cert \
  --from-file=cert.pem=/tmp/cert.pem \
  --from-file=key.pem=/tmp/key.pem \
  -n east

# 3. Deploy
kubectl apply -f deployment-tls.yaml
kubectl apply -f service-tls.yaml
```

### 3. Verify TLS Backend

```bash
# Check pod logs
kubectl logs -n east -l app=getback-tls

# Should see:
# Starting Get-Back (TLS enabled) | HTTP:9091 TCP:9092 Dashboard:9093
# ✓ HTTPS ready on 0.0.0.0:9091
# ✓ TLS-TCP ready on 0.0.0.0:9092

# Test from another pod
kubectl run -n east curl-test --rm -i --image=curlimages/curl -- \
  curl -k https://getback-tls:9091/

# Expected: {"counter":1,"server":"east-tls","timestamp":...}
```

### 4. Test from Dashboard

```bash
# Port-forward dashboard
kubectl port-forward -n west svc/getback-dashboard 9093:9093

# Open browser: http://localhost:9093/

# Test plain backend:
# Backend: getback.east:9091
# TLS: unchecked
# Click "Send HTTP Request" → Success

# Test TLS backend:
# Backend: getback-tls.east:9091
# TLS: checked
# Click "Send HTTP Request" → Success
```

## Architecture Details

### Native Python TLS (Zero Dependencies)

The implementation uses Python's built-in `ssl` and `asyncio` modules:

**Server side (`__main__.py`):**
```python
import ssl

def create_server_ssl_context(cert_path: str, key_path: str):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    return context

# Pass to asyncio.start_server()
server = await asyncio.start_server(handler, host, port, ssl=ssl_context)
```

**Client side (dashboard):**
```python
# Already implemented - permissive context for self-signed certs
def create_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

ssl_context = create_ssl_context() if use_tls else None
reader, writer = await asyncio.open_connection(host, port, ssl=ssl_context)
```

### Environment Variables

- `TLS_CERT_PATH` - Path to TLS certificate file
- `TLS_KEY_PATH` - Path to TLS private key file

Both must be set to enable TLS. If either is empty/unset, server runs in plain mode.

### CLI Arguments

```bash
--tls-cert /path/to/cert.pem
--tls-key /path/to/key.pem
```

CLI arguments override environment variables.

## Troubleshooting

### "SSL: CERTIFICATE_VERIFY_FAILED"

**Problem:** Client rejects self-signed certificate

**Solution:** Dashboard already uses permissive SSL context. If testing with curl/openssl, use `-k` or `-quiet` flags.

### "FileNotFoundError: cert.pem"

**Problem:** Certificate file not found

**Solution:** 
- Check path is correct: `ls -l /etc/tls/cert.pem`
- Verify secret is mounted: `kubectl describe pod -n east <pod-name>`
- Check volume mount in deployment YAML

### "SSL: TLSV1_ALERT_UNKNOWN_CA"

**Problem:** Client validating against CA store

**Solution:** Dashboard uses `verify_mode = ssl.CERT_NONE` to accept self-signed certs

### Server starts but TLS doesn't work

**Problem:** Both `TLS_CERT_PATH` and `TLS_KEY_PATH` must be set

**Solution:**
```bash
# Check env vars are set
kubectl exec -n east <pod-name> -- env | grep TLS

# Should see:
# TLS_CERT_PATH=/etc/tls/cert.pem
# TLS_KEY_PATH=/etc/tls/key.pem
```

## Implementation Details

### Native Python TLS Approach
- ✓ Single container per pod
- ✓ Zero external dependencies
- ✓ Simple configuration (2 env vars)
- ✓ Lower resource usage
- ✓ Direct TLS handling via asyncio
- ✓ Consistent with "zero dependencies" philosophy
