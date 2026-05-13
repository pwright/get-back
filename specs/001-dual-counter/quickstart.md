# Quickstart Guide: Dual-Protocol Counter Service

**Feature**: Dual-Protocol Counter Service  
**Version**: 1.0  
**Date**: 2026-05-13

## What is This?

A simple network service that exposes incrementing counters via HTTP and TCP protocols. Designed for demonstrating and testing load balancer behavior with different connection patterns.

**Use Cases**:
- Verify load balancer round-robin distribution
- Test persistent vs. ephemeral connection handling
- Demonstrate Layer 4 (TCP) vs. Layer 7 (HTTP) load balancing
- Quick network connectivity testing

## Quick Start (5 minutes)

### 1. Install

```bash
# Clone repository
git clone <repo-url>
cd get-back

# No dependencies needed for server (Python 3.11+ standard library only)
# Optional: Install test dependencies
pip install -r requirements-dev.txt
```

### 2. Run Server

```bash
# Run with defaults (HTTP: 9091, TCP: 9092)
python -m getback

# Or customize ports
python -m getback --http-port 8080 --tcp-port 8090

# Or use environment variables
export HTTP_PORT=8080
export TCP_PORT=8090
python -m getback
```

**Expected Output**:
```
2026-05-13 10:30:00 [INFO] getback: Starting Dual-Protocol Counter Service
2026-05-13 10:30:00 [INFO] getback.http: HTTP server listening on 0.0.0.0:9091
2026-05-13 10:30:00 [INFO] getback.tcp: TCP server listening on 0.0.0.0:9092
2026-05-13 10:30:00 [INFO] getback: Server ready. Press Ctrl+C to stop.
```

### 3. Test HTTP Endpoint

```bash
# Simple curl request
$ curl http://localhost:9091/
1

$ curl http://localhost:9091/
2

$ curl http://localhost:9091/anything
3
```

**Explanation**: Each request increments the HTTP counter independently. Any path works.

### 4. Test TCP Endpoint

**Immediate Close**:
```bash
$ echo "hello" | nc localhost 9092
1
```

**Timed Connection (5 seconds)**:
```bash
$ echo "5" | nc localhost 9092
2
# Connection stays open for 5 seconds, then closes
```

**Persistent Connection**:
```bash
$ echo "OPEN" | nc localhost 9092
3
# Connection stays open until you close nc (Ctrl+C)
```

## Using Sample Clients

Pre-built clients are in the `clients/` directory.

### HTTP Client

```bash
# Basic usage
python clients/http_client.py http://localhost:9091

# Output: Counter: 1

# Run multiple times
for i in {1..5}; do
  python clients/http_client.py http://localhost:9091
done
# Output: Counter: 1, 2, 3, 4, 5
```

### TCP Client

```bash
# Immediate close
python clients/tcp_client.py localhost 9092 test
# Output: Counter: 1, Duration: 0.01s

# 3 second connection
python clients/tcp_client.py localhost 9092 3
# Output: Counter: 2, Duration: 3.02s

# Persistent connection (Ctrl+C to stop)
python clients/tcp_client.py localhost 9092 OPEN
# Output: Counter: 3, Duration: (persistent until Ctrl+C)
```

## Load Balancer Testing Scenarios

### Scenario 1: HTTP Round-Robin

**Setup**: Run 3 instances on different ports

**Terminal 1**:
```bash
python -m getback --http-port 9091 --tcp-port 9092
```

**Terminal 2**:
```bash
python -m getback --http-port 9191 --tcp-port 9192
```

**Terminal 3**:
```bash
python -m getback --http-port 9291 --tcp-port 9292
```

**Configure Load Balancer** (example with HAProxy):
```
frontend http_front
    bind *:8080
    default_backend http_back

backend http_back
    balance roundrobin
    server s1 localhost:9091
    server s2 localhost:9191
    server s3 localhost:9291
```

**Test**:
```bash
$ curl http://localhost:8080/
1   # Backend 1
$ curl http://localhost:8080/
1   # Backend 2
$ curl http://localhost:8080/
1   # Backend 3
$ curl http://localhost:8080/
2   # Backend 1
```

**Expected**: Each backend counter increments independently, demonstrating distribution.

### Scenario 2: TCP Persistent Connection Load Balancing

**Setup**: Same 3 instances as above

**Configure Load Balancer** (HAProxy):
```
frontend tcp_front
    bind *:7000
    mode tcp
    default_backend tcp_back

backend tcp_back
    mode tcp
    balance leastconn  # Route to backend with fewest active connections
    server s1 localhost:9092
    server s2 localhost:9192
    server s3 localhost:9292
```

**Test**:
```bash
# Open 3 persistent connections (run in background)
(echo "OPEN" | nc localhost 7000 &)  # → Backend 1
(echo "OPEN" | nc localhost 7000 &)  # → Backend 2
(echo "OPEN" | nc localhost 7000 &)  # → Backend 3

# New request should distribute based on least connections
echo "test" | nc localhost 7000
# → Should go to any backend (all have 1 OPEN connection)

# Open another persistent on Backend 1
(echo "OPEN" | nc localhost 7000 &)  # → Backend 1 (now has 2 connections)

# New request should avoid Backend 1
echo "test" | nc localhost 7000
# → Backend 2 or 3 (both have 1 connection vs Backend 1's 2)
```

### Scenario 3: Timed Connections (Connection Duration Awareness)

**Test connection duration impact on load distribution**:

```bash
# Send requests with 10-second connection lifetime
for i in {1..6}; do
  (echo "10" | nc localhost 7000 &)
  sleep 1  # Stagger by 1 second
done

# Watch load distribution
# First 3 requests: Distributed to each backend (1 connection each)
# Requests 4-6: Round-robin continues, each backend gets 2 connections
# After 10 seconds: All connections close, counters: 2, 2, 2
```

## Configuration

### Command-Line Arguments

```
python -m getback [OPTIONS]

Options:
  --http-port PORT       HTTP server port (default: 9091)
  --tcp-port PORT        TCP server port (default: 9092)  
  --host HOST            Bind address (default: 0.0.0.0)
  --log-level LEVEL      Logging level: DEBUG|INFO|WARNING|ERROR (default: INFO)
  -h, --help             Show help message
```

### Environment Variables

Fallback if CLI args not provided:

- `HTTP_PORT`: HTTP server port
- `TCP_PORT`: TCP server port
- `HOST`: Bind address
- `LOG_LEVEL`: Logging level

**Priority**: CLI args > Environment variables > Defaults

### Examples

```bash
# Custom ports via CLI
python -m getback --http-port 8080 --tcp-port 8090

# Custom ports via env vars
export HTTP_PORT=8080 TCP_PORT=8090
python -m getback

# Debug logging
python -m getback --log-level DEBUG

# Bind to localhost only (not all interfaces)
python -m getback --host 127.0.0.1
```

## Docker Deployment

### Build Image

```bash
docker build -t getback:latest .
```

### Run Container

```bash
# Default ports (9091 HTTP, 9092 TCP)
docker run -p 9091:9091 -p 9092:9092 getback:latest

# Custom ports
docker run -p 8080:8080 -p 8090:8090 \
  -e HTTP_PORT=8080 -e TCP_PORT=8090 \
  getback:latest

# With debug logging
docker run -p 9091:9091 -p 9092:9092 \
  -e LOG_LEVEL=DEBUG \
  getback:latest
```

### Docker Compose (3 Instances)

```yaml
version: '3'
services:
  backend1:
    build: .
    ports:
      - "9091:9091"
      - "9092:9092"
  
  backend2:
    build: .
    ports:
      - "9191:9091"
      - "9192:9092"
  
  backend3:
    build: .
    ports:
      - "9291:9091"
      - "9292:9092"
```

```bash
docker-compose up
```

## Kubernetes Deployment (Skaffold)

### Prerequisites

```bash
# Install Skaffold (https://skaffold.dev/docs/install/)
curl -Lo skaffold https://storage.googleapis.com/skaffold/releases/latest/skaffold-linux-amd64
sudo install skaffold /usr/local/bin/

# Ensure you have a Kubernetes cluster running
# - Docker Desktop: Enable Kubernetes in settings
# - minikube: minikube start
# - kind: kind create cluster
# - k3d: k3d cluster create
```

### Development Workflow (Live Reload)

```bash
# Start development mode with auto-rebuild and hot reload
skaffold dev

# Skaffold will:
# 1. Build the Docker image
# 2. Deploy to Kubernetes (3 replicas)
# 3. Port-forward 9091 and 9092 to localhost
# 4. Watch for Python file changes and sync to pods
# 5. Stream logs from all pods
```

**Expected Output**:
```
Generating tags...
 - getback -> getback:latest
Checking cache...
 - getback: Not found. Building
Starting build...
Building [getback]...
Tags used in deployment:
 - getback -> getback:abc123
Starting deploy...
 - deployment.apps/getback created
 - service/getback created
Waiting for deployments to stabilize...
 - deployment/getback: 3/3 pods ready
Deployments stabilized in 5.2 seconds
Port forwarding service/getback in namespace default, remote port 9091 -> 127.0.0.1:9091
Port forwarding service/getback in namespace default, remote port 9092 -> 127.0.0.1:9092
Press Ctrl+C to exit
```

### Production-Like Deployment

```bash
# Deploy without file watching
skaffold run

# Clean up deployment
skaffold delete
```

### Testing Load Balancing

**Verify 3 pods are running**:
```bash
kubectl get pods -l app=getback
# NAME                      READY   STATUS    RESTARTS   AGE
# getback-7d4f8c6b9-abc12   1/1     Running   0          30s
# getback-7d4f8c6b9-def34   1/1     Running   0          30s
# getback-7d4f8c6b9-ghi56   1/1     Running   0          30s
```

**Test HTTP load balancing** (each pod has independent counter):
```bash
# Make 9 requests - should hit each pod 3 times
for i in {1..9}; do
  curl http://localhost:9091/
done
# Expected pattern: 1,1,1,2,2,2,3,3,3 (round-robin across 3 pods)
```

**Test TCP load balancing**:
```bash
# 6 immediate-close connections
for i in {1..6}; do
  echo "test" | nc localhost 9092
done
# Expected: Each pod counter: 2, 2, 2
```

**Observe which pod handled the request**:
```bash
# Watch logs from all pods
kubectl logs -l app=getback --tail=10 -f

# In another terminal, make requests
curl http://localhost:9091/

# Look for log entries showing which pod incremented counter
```

### Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment getback --replicas=5

# Verify
kubectl get pods -l app=getback

# Test distribution across 5 pods
for i in {1..10}; do curl http://localhost:9091/; done
# Expected: Each pod counter ~2 (10 requests / 5 pods)
```

### Accessing Service Without Port-Forward

**Using kubectl port-forward** (manual):
```bash
kubectl port-forward service/getback 9091:9091 9092:9092
```

**Using LoadBalancer** (if supported by your cluster):
```bash
# Get external IP
kubectl get service getback
# NAME      TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)
# getback   LoadBalancer   10.96.100.200   <pending>     9091:30123/TCP,9092:30124/TCP

# On cloud clusters (GKE, EKS, AKS), EXTERNAL-IP will be assigned
# curl http://<EXTERNAL-IP>:9091/
```

**Using NodePort** (for local clusters like minikube):

Edit `k8s/service.yaml` and change `type: LoadBalancer` to `type: NodePort`, then:
```bash
# Redeploy
skaffold delete && skaffold run

# Get node port
kubectl get service getback
# PORT(S): 9091:30123/TCP,9092:30124/TCP
#               ^^^^^ NodePort

# Access via node IP
# minikube: minikube ip (e.g., 192.168.49.2)
curl http://$(minikube ip):30123/
echo "test" | nc $(minikube ip) 30124
```

### Debugging

**View logs from all pods**:
```bash
kubectl logs -l app=getback --tail=50
```

**View logs from specific pod**:
```bash
kubectl logs getback-7d4f8c6b9-abc12
```

**Exec into pod**:
```bash
kubectl exec -it getback-7d4f8c6b9-abc12 -- /bin/bash

# Inside pod, test locally
curl http://localhost:9091/
echo "test" | nc localhost 9092
```

**Check service endpoints**:
```bash
kubectl get endpoints getback
# Should show 3 pod IPs with ports 9091,9092
```

### Configuration

**Override environment variables**:

Edit `k8s/deployment.yaml` env section:
```yaml
env:
- name: HTTP_PORT
  value: "8080"  # Changed from 9091
- name: LOG_LEVEL
  value: "DEBUG"
```

Then redeploy:
```bash
skaffold delete && skaffold run
```

**Use ConfigMap** (optional, for production):

Create `k8s/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: getback-config
data:
  HTTP_PORT: "9091"
  TCP_PORT: "9092"
  LOG_LEVEL: "INFO"
```

Reference in `deployment.yaml`:
```yaml
envFrom:
- configMapRef:
    name: getback-config
```

### Client Deployments on Kubernetes

Run clients as Jobs or continuous load generators:

**One-off HTTP test**:
```bash
kubectl apply -f k8s/client-http-job.yaml
kubectl logs job/http-client-test -f
# Output: Counter: 1, 2, 3, ..., 10
```

**One-off TCP test**:
```bash
kubectl apply -f k8s/client-tcp-job.yaml
kubectl logs job/tcp-client-test -f
# Tests immediate, 3s, and 5s connections
```

**Continuous load generation** (2 pods making requests every few seconds):
```bash
kubectl apply -f k8s/client-load-generator.yaml

# Watch server logs to see load distribution
kubectl logs -l app=getback --tail=20 -f

# Scale load up
kubectl scale deployment load-generator --replicas=5

# Stop load
kubectl delete deployment load-generator
```

**Periodic health checks** (CronJob every 5 minutes):
```bash
kubectl apply -f k8s/client-cronjob.yaml
kubectl get jobs --watch
```

See [k8s/README.md](../../k8s/README.md) for detailed client deployment guide.

### Cleanup

```bash
# Delete client resources
kubectl delete job http-client-test tcp-client-test --ignore-not-found
kubectl delete deployment load-generator --ignore-not-found
kubectl delete cronjob periodic-health-check --ignore-not-found

# Delete server
skaffold delete

# Or manually
kubectl delete deployment getback
kubectl delete service getback
```

## Testing

### Run Unit Tests

```bash
# Install test dependencies (pytest)
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_counter.py

# Run with coverage
pytest --cov=getback --cov-report=html

# Run integration tests only
pytest tests/test_integration.py
```

### Manual Testing Checklist

**HTTP Endpoint**:
- [ ] `curl http://localhost:9091/` returns 1
- [ ] Subsequent requests increment: 2, 3, 4...
- [ ] Different paths work: `/`, `/anything`, `/api/test`
- [ ] POST/PUT/DELETE methods work same as GET

**TCP Endpoint**:
- [ ] `echo "test" | nc localhost 9092` returns 1, closes immediately
- [ ] `echo "5" | nc localhost 9092` returns counter, waits ~5 seconds
- [ ] `echo "OPEN" | nc localhost 9092` stays open until Ctrl+C
- [ ] Invalid numbers treated as arbitrary text (immediate close)

**Counter Independence**:
- [ ] HTTP counter and TCP counter increment independently
- [ ] HTTP request doesn't affect TCP counter value
- [ ] TCP request doesn't affect HTTP counter value

**Concurrency**:
- [ ] Multiple simultaneous requests get unique counter values
- [ ] No duplicates under concurrent load
- [ ] `ab -n 100 -c 10 http://localhost:9091/` completes successfully

**Configuration**:
- [ ] Custom ports work: `--http-port 8080 --tcp-port 8090`
- [ ] Environment variables work: `HTTP_PORT=8080 python -m getback`
- [ ] Logging levels work: `--log-level DEBUG` shows extra output

**Error Handling**:
- [ ] Port already in use → Server logs error and exits
- [ ] Client disconnect → Server logs and continues serving
- [ ] Invalid TCP command → Treated as arbitrary (immediate close)

## Troubleshooting

### Server Won't Start

**Error**: `Address already in use`
```
ERROR: HTTP server bind failed: [Errno 48] Address already in use
```

**Solution**: Port already in use. Find and kill process:
```bash
# Find process using port 9091
lsof -i :9091

# Kill it
kill -9 <PID>

# Or use different port
python -m getback --http-port 9095
```

### Can't Connect from Other Machines

**Problem**: `curl http://<server-ip>:9091/` times out from another machine

**Possible Causes**:
1. Firewall blocking ports 9091/9092
2. Server bound to localhost only (127.0.0.1)

**Solutions**:
```bash
# Check server is bound to 0.0.0.0 (all interfaces)
netstat -an | grep 9091

# Ensure server started with --host 0.0.0.0 (default) or --host <server-ip>
python -m getback --host 0.0.0.0

# Open firewall (Ubuntu/Debian)
sudo ufw allow 9091/tcp
sudo ufw allow 9092/tcp
```

### Counters Not Incrementing

**Problem**: All requests return same counter value

**Cause**: Multiple server instances writing to same counter (impossible with this design)

**Verification**: Should never happen - each server instance has isolated in-memory counters

### TCP Connection Doesn't Close After Timeout

**Problem**: Sent `echo "5" | nc localhost 9092`, but connection stayed open longer

**Expected Behavior**: Connection duration = ~5 seconds ±50ms (asyncio sleep granularity)

**If Duration Wrong**:
- Check server logs for timing info (DEBUG level)
- Ensure command was exactly `"5\n"` not `"5 \n"` (extra space)
- Verify number parsing (non-integer treated as arbitrary → immediate close)

## Next Steps

- Read [HTTP Protocol Contract](contracts/http-protocol.md) for detailed HTTP API
- Read [TCP Protocol Contract](contracts/tcp-protocol.md) for detailed TCP protocol
- Review [Data Model](data-model.md) for architecture understanding
- Check [Implementation Plan](plan.md) for design decisions
- Explore [clients/README.md](../../clients/README.md) for client examples

## Support & Issues

This is a demonstration tool, not production software. For questions or issues:
- Check protocol contracts for expected behavior
- Review test suite for examples
- Inspect logs with `--log-level DEBUG`
