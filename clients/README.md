# Get-Back Sample Clients

Sample client implementations for testing the Get-Back dual-protocol counter service.

## HTTP Client

Simple HTTP client using Python's urllib (standard library).

### Usage

```bash
python clients/http_client.py <url>
```

### Examples

```bash
# Request counter from local server
python clients/http_client.py http://localhost:9091/

# Request from different path (still increments counter)
python clients/http_client.py http://localhost:9091/anything

# Health check (doesn't increment counter)
python clients/http_client.py http://localhost:9091/health

# Request from load-balanced endpoint
python clients/http_client.py http://load-balancer:8080/
```

### Load Testing Example

```bash
# Make 100 requests and observe counter progression
for i in {1..100}; do
  python clients/http_client.py http://localhost:9091/
done
```

## TCP Client

TCP client supporting all three command modes.

### Usage

```bash
python clients/tcp_client.py <host> <port> <command>
```

**Commands**:
- `<number>` - Connection stays open for N seconds (e.g., `5`)
- `OPEN` - Persistent connection (press Ctrl+C to close)
- `<other>` - Any other text causes immediate close

### Examples

**Immediate Close**:
```bash
python clients/tcp_client.py localhost 9092 test
# Output:
# Connected to localhost:9092
# Counter: 1
# Duration: 0.01s
```

**Timed Connection (5 seconds)**:
```bash
python clients/tcp_client.py localhost 9092 5
# Output:
# Connected to localhost:9092
# Counter: 2
# Duration: 5.02s
```

**Persistent Connection**:
```bash
python clients/tcp_client.py localhost 9092 OPEN
# Output:
# Connected to localhost:9092
# Counter: 3
# Connection persistent (Ctrl+C to close)...
# [waits until you press Ctrl+C]
# ^C
# Closing connection...
# Duration: 12.34s
```

## Load Balancer Testing Scenarios

### Scenario 1: HTTP Round-Robin

**Setup**: 3 backend servers, HAProxy round-robin load balancer

```bash
# Terminal 1: Backend 1
python -m getback --http-port 9091 --tcp-port 9092

# Terminal 2: Backend 2
python -m getback --http-port 9191 --tcp-port 9192

# Terminal 3: Backend 3
python -m getback --http-port 9291 --tcp-port 9292

# Terminal 4: HAProxy (configure to round-robin across :9091, :9191, :9291)
# Then test:
for i in {1..9}; do
  python clients/http_client.py http://localhost:8080/
done

# Expected output:
# Counter: 1  (backend 1)
# Counter: 1  (backend 2)
# Counter: 1  (backend 3)
# Counter: 2  (backend 1)
# Counter: 2  (backend 2)
# Counter: 2  (backend 3)
# Counter: 3  (backend 1)
# Counter: 3  (backend 2)
# Counter: 3  (backend 3)
```

### Scenario 2: TCP Least Connections

**Setup**: Same 3 backends, HAProxy with least-connections for TCP

```bash
# Open 3 persistent connections
python clients/tcp_client.py localhost 7000 OPEN &  # → Backend 1
python clients/tcp_client.py localhost 7000 OPEN &  # → Backend 2
python clients/tcp_client.py localhost 7000 OPEN &  # → Backend 3

# Now each backend has 1 persistent connection
# New requests distribute evenly:
for i in {1..6}; do
  python clients/tcp_client.py localhost 7000 test
done

# Each backend counter should be at 3 (1 OPEN + 2 immediate)
```

### Scenario 3: Kubernetes Load Balancing

**Using Skaffold deployment** (3 replicas):

```bash
# Start deployment
skaffold dev

# Test HTTP distribution
for i in {1..12}; do
  python clients/http_client.py http://localhost:9091/
done
# Expected: 1,1,1,1,2,2,2,2,3,3,3,3 (4 requests per pod)

# Test TCP timed connections
for i in {1..6}; do
  (python clients/tcp_client.py localhost 9092 10 &)
  sleep 1
done
# All 6 connections active for ~10 seconds
# Distributed across 3 pods (2 per pod)
```

## Verifying Counter Independence

HTTP and TCP counters are independent. You can verify this:

```bash
# Make 3 HTTP requests
python clients/http_client.py http://localhost:9091/  # Counter: 1
python clients/http_client.py http://localhost:9091/  # Counter: 2
python clients/http_client.py http://localhost:9091/  # Counter: 3

# Make TCP request - starts from 1 (independent counter)
python clients/tcp_client.py localhost 9092 test      # Counter: 1

# HTTP counter continues from 3
python clients/http_client.py http://localhost:9091/  # Counter: 4

# TCP counter continues from 1
python clients/tcp_client.py localhost 9092 test      # Counter: 2
```

## Health Check Testing

Health endpoint doesn't increment the counter:

```bash
# Initial counter request
python clients/http_client.py http://localhost:9091/
# Counter: 1

# Health check (doesn't increment)
python clients/http_client.py http://localhost:9091/health
# Counter: OK

# Another counter request (still 2, not 3)
python clients/http_client.py http://localhost:9091/
# Counter: 2
```

## Using with curl and netcat

You don't need Python clients - standard tools work too:

**HTTP**:
```bash
curl http://localhost:9091/        # Counter: 1
curl http://localhost:9091/health  # OK
```

**TCP**:
```bash
echo "test" | nc localhost 9092    # Counter: 1
echo "5" | nc localhost 9092       # Counter: 2 (waits 5s)
echo "OPEN" | nc localhost 9092    # Counter: 3 (persistent until Ctrl+C)
```

## Troubleshooting

**Connection Refused**:
- Ensure server is running: `python -m getback`
- Check ports are correct (HTTP: 9091, TCP: 9092 by default)

**Wrong Counter Values**:
- Remember HTTP and TCP have separate counters
- Health endpoint (`/health`) doesn't increment counter
- Each server instance has its own counters (in load-balanced setups)

**TCP Timing Issues**:
- Numeric command duration is approximate (±50-200ms due to asyncio sleep granularity)
- Network latency adds to measured duration
- Use `--log-level DEBUG` on server to see exact timing

## Requirements

Clients use Python 3.6+ standard library only:
- `urllib.request` (HTTP client)
- `socket` (TCP client)
- `time` (duration measurement)

No pip packages needed!
