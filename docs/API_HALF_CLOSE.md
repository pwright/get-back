# Using the API for Half-Close Testing

The dashboard API supports half-close testing through the `/api/request/tcp` endpoint.

## Quick Start

### Test HALF_CLOSE_SEND via API

```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "localhost:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 10,
    "tls": false
  }'
```

**Response**:
```json
{
  "results": [
    {
      "counter": 1,
      "server": "hostname-abc",
      "latency_ms": 15,
      "command": "HALF_CLOSE_SEND",
      "timestamp": 1234567890123
    },
    ...
  ],
  "total": 10,
  "successful": 10
}
```

### Test HALF_CLOSE_READ via API

```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "localhost:9092",
    "command": "HALF_CLOSE_READ",
    "amount": 5,
    "tls": false
  }'
```

## API Commands

The `/api/request/tcp` endpoint accepts these commands:

| Command | Behavior | Use Case |
|---------|----------|----------|
| `test` | Immediate close | Quick connectivity test |
| `5` (numeric) | Timed (5s) | Test timed connections |
| `OPEN` | Persistent | Test long-lived connections |
| `HALF_CLOSE_SEND` | Server sends FIN first | Test FIN_WAIT_1 behavior |
| `HALF_CLOSE_READ` | Client sends FIN first | Test FIN detection |

## Request Schema

```json
{
  "backend": "string (host:port)",
  "command": "string",
  "amount": "integer (1-10000)",
  "tls": "boolean (default: false)"
}
```

### Fields

- **backend**: Backend server in `host:port` format
  - Examples: `localhost:9092`, `getback:9092`, `skupper-listener:9092`
  
- **command**: TCP command to send
  - `HALF_CLOSE_SEND` - Server sends response, shuts down write side (FIN), keeps reading
  - `HALF_CLOSE_READ` - Server reads until client FIN, then closes
  - `test` - Immediate close
  - `OPEN` - Persistent connection
  - Numeric (e.g., `"5"`) - Timed connection

- **amount**: Number of concurrent requests (server-side batching)
  - Minimum: 1
  - Maximum: 10000
  - Default: 10

- **tls**: Use TLS encryption
  - `true` - Connect with TLS (⚠️ half-close not fully supported over TLS in Python)
  - `false` - Plain TCP (recommended for half-close testing)

## Response Schema

```json
{
  "results": [
    {
      "counter": 1,
      "server": "hostname-abc",
      "latency_ms": 15,
      "command": "HALF_CLOSE_SEND",
      "timestamp": 1234567890123
    }
  ],
  "total": 10,
  "successful": 10
}
```

### Fields

- **results**: Array of successful request results
- **total**: Total requests attempted
- **successful**: Number of successful requests (may be < total if errors occurred)

Each result contains:
- **counter**: Backend counter value
- **server**: Backend server hostname/pod name
- **latency_ms**: Round-trip latency in milliseconds
- **command**: TCP command that was sent
- **timestamp**: Unix timestamp in milliseconds

## Examples

### Example 1: Test Server-Initiated FIN

Test if skupper correctly forwards server FIN packets:

```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "skupper-listener:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 1
  }'
```

**Expected**: Successfully receives counter response and connection closes cleanly.

**Failure mode**: If skupper drops/converts FIN, the connection may hang or reset.

### Example 2: Test Client-Initiated FIN Detection

Test if skupper signals client FIN to the server:

```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "skupper-listener:9092",
    "command": "HALF_CLOSE_READ",
    "amount": 1
  }'
```

**Expected**: Server detects client FIN and closes normally.

**Failure mode**: If skupper doesn't signal EOF, server may wait indefinitely.

### Example 3: Batch Testing

Send multiple half-close tests concurrently:

```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "getback:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 100
  }'
```

**Result**: 100 concurrent half-close tests, useful for:
- Load testing half-close behavior
- Observing distribution across backend pods
- Stress testing skupper router

### Example 4: Using jq to Extract Data

```bash
curl -s -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "localhost:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 10
  }' | jq '{
    total: .total,
    successful: .successful,
    servers: [.results[].server] | unique,
    avg_latency: ([.results[].latency_ms] | add / length)
  }'
```

**Output**:
```json
{
  "total": 10,
  "successful": 10,
  "servers": ["backend-1", "backend-2"],
  "avg_latency": 12.5
}
```

## Integration Examples

### Python

```python
import requests
import json

response = requests.post(
    'http://localhost:9093/api/request/tcp',
    json={
        'backend': 'localhost:9092',
        'command': 'HALF_CLOSE_SEND',
        'amount': 10,
        'tls': False
    }
)

data = response.json()
print(f"Successful: {data['successful']}/{data['total']}")
for result in data['results']:
    print(f"  Server: {result['server']}, Latency: {result['latency_ms']}ms")
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:9093/api/request/tcp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    backend: 'localhost:9092',
    command: 'HALF_CLOSE_SEND',
    amount: 10,
    tls: false
  })
});

const data = await response.json();
console.log(`Successful: ${data.successful}/${data.total}`);
data.results.forEach(r => {
  console.log(`  ${r.server}: ${r.latency_ms}ms`);
});
```

### Bash Script

```bash
#!/bin/bash

# Test both half-close modes
for cmd in HALF_CLOSE_SEND HALF_CLOSE_READ; do
  echo "Testing $cmd..."
  
  response=$(curl -s -X POST http://localhost:9093/api/request/tcp \
    -H "Content-Type: application/json" \
    -d "{
      \"backend\": \"localhost:9092\",
      \"command\": \"$cmd\",
      \"amount\": 5
    }")
  
  successful=$(echo "$response" | jq -r '.successful')
  total=$(echo "$response" | jq -r '.total')
  
  if [ "$successful" -eq "$total" ]; then
    echo "✓ $cmd: All $total requests succeeded"
  else
    echo "✗ $cmd: Only $successful/$total succeeded"
  fi
done
```

## TLS Limitations

**⚠️ Important**: The dashboard API uses Python's asyncio client, which has TLS half-close limitations:

- ✅ **Plain TCP**: Full half-close support via `HALF_CLOSE_SEND` and `HALF_CLOSE_READ`
- ⚠️ **TLS**: Limited support - Python's SSL module doesn't properly support half-close

**For TLS half-close testing**, use the Go CLI client instead:

```bash
./halfclose_client -host localhost -port 9092 -tls -insecure
```

The API will accept `"tls": true` but the half-close behavior may not work correctly over TLS connections.

## Error Handling

### Backend Unavailable

**Request**:
```bash
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "nonexistent:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 1
  }'
```

**Response**:
```json
{
  "results": [],
  "total": 1,
  "successful": 0
}
```

The API returns partial results - failed requests are omitted from `results` array.

### Invalid Backend Format

**Response**: HTTP 502 Bad Gateway
```json
{
  "error": "Invalid backend format"
}
```

## Monitoring Half-Close Tests

### View Statistics

```bash
curl -s http://localhost:9093/stats | jq '.latency.tcp'
```

**Output**:
```json
{
  "min": 5,
  "max": 150,
  "avg": 25,
  "p50": 20,
  "p95": 75,
  "p99": 120,
  "count": 1000
}
```

### View Distribution

```bash
curl -s http://localhost:9093/api/distribution | jq
```

**Output**:
```json
{
  "distribution": {
    "backend-1": {
      "count": 523,
      "percent": 52.3
    },
    "backend-2": {
      "count": 477,
      "percent": 47.7
    }
  },
  "total": 1000,
  "timestamp": 1234567890
}
```

## OpenAPI Specification

Full API documentation available at:

```bash
# OpenAPI JSON
curl http://localhost:9093/openapi.json

# Or view in Swagger UI
open http://localhost:9093/  # Opens interactive dashboard
```

The OpenAPI spec includes:
- Full schema definitions
- Example requests for all command types
- Response schemas
- Error responses

## Testing Scenarios

### Scenario 1: Baseline Testing

Test half-close locally before testing through skupper:

```bash
# Start server
python -m getback &

# Test via API
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{"backend": "localhost:9092", "command": "HALF_CLOSE_SEND", "amount": 1}'

# Should show successful: 1/1
```

### Scenario 2: Skupper Testing

Test half-close through skupper router:

```bash
# Expose backend via skupper
skupper expose deployment/getback --port 9092

# Test via API through skupper
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{"backend": "skupper-listener:9092", "command": "HALF_CLOSE_SEND", "amount": 10}'
```

### Scenario 3: Load Testing

Stress test half-close behavior:

```bash
# 1000 concurrent half-close tests
curl -X POST http://localhost:9093/api/request/tcp \
  -H "Content-Type: application/json" \
  -d '{
    "backend": "skupper-listener:9092",
    "command": "HALF_CLOSE_SEND",
    "amount": 1000
  }'
```

## Comparison: API vs CLI Clients

| Feature | Dashboard API | Python CLI | Go CLI |
|---------|---------------|------------|--------|
| Plain TCP half-close | ✅ | ✅ | ✅ |
| TLS half-close | ⚠️ Limited | ❌ | ✅ |
| Batch testing | ✅ | ❌ | ❌ |
| Server-side execution | ✅ | ❌ | ❌ |
| Scriptable | ✅ | ✅ | ✅ |
| GUI integration | ✅ | ❌ | ❌ |

**Use API when**:
- Testing from automation/CI
- Need batch/concurrent testing
- Monitoring distribution
- Dashboard already running

**Use CLI clients when**:
- Need detailed step-by-step output
- Testing TLS half-close (Go only)
- Quick manual verification
- Dashboard not available

## See Also

- [HALF_CLOSE.md](HALF_CLOSE.md) - General half-close documentation
- [HALF_CLOSE_TLS.md](HALF_CLOSE_TLS.md) - TLS-specific documentation
- [clients/GO_CLIENT.md](../clients/GO_CLIENT.md) - Go client reference
- OpenAPI spec: http://localhost:9093/openapi.json
