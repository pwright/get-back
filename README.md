# Get-Back: Dual-Protocol Counter Service

A network service with HTTP and TCP counters, plus an **interactive web console** for real-time load balancing demonstration. Perfect for testing service meshes, load balancers, and multi-cluster networking.

**Ports:**
- 🎯 **Dashboard**: 9093 (Interactive console with request distribution visualization)
- 📡 **TCP**: 9092 (Command-based protocol)
- 🌐 **HTTP**: 9091 (REST counter endpoint)

## Quick Start: Skupper Multi-Cluster

Deploy across multiple sites (east, west) with Skupper service mesh:

```bash
# Deploy to west cluster
kubectl apply -f west/deployment.yaml
kubectl apply -f west/service.yaml      # ← Local service access
kubectl apply -f west/connectors.yaml   # ← Expose to Skupper network
kubectl apply -f west/listeners.yaml    # ← Aggregate all sites

# Deploy to east cluster  
kubectl apply -f east/deployment.yaml
kubectl apply -f east/connectors.yaml   # ← Expose to Skupper network

# Access the console
kubectl port-forward -n west svc/getback 9093:9093
# Open http://localhost:9093/
```

**Directory structure:**
```
west/
├── deployment.yaml    # 1 replica, quay.io image, namespace: west
├── service.yaml       # ClusterIP for dashboard only (getback-dashboard)
├── connectors.yaml    # Skupper connectors (expose to network)
└── listeners.yaml     # Skupper listeners (aggregate sites)

east/
├── deployment.yaml    # 1 replica, quay.io image, namespace: east
└── connectors.yaml    # Skupper connectors
```

**Interactive console features:**
- Set **Amount** to send N concurrent requests (e.g., 100)
- Click buttons to send HTTP/TCP requests
- **Distribution panel** shows breakdown per pod/site
- Watch real-time load balancing across clusters!

![Distribution Panel](image-1.png)

**Prerequisites:** Push image to `quay.io/pwright/getback:latest` (or update image refs)

## Quick Start: Local Development

```bash
# Run locally
python -m getback

# Open interactive dashboard
open http://localhost:9093/
# Or visit in browser and click "Send HTTP Request" button

# Test HTTP endpoint directly
curl http://localhost:9091/  # Returns: 1 (hostname)

# Test TCP endpoint
echo "test" | nc localhost 9092  # Returns: 1 (hostname)

# Test with server identity
curl http://localhost:9091/  # Returns: 2 (laptop.local)
echo "OPEN" | nc localhost 9092  # Returns: 2 (laptop.local) - persistent
```

## Features

### Core Protocol Support
- **Dual Protocol**: HTTP (port 9091) and TCP (port 9092)
- **Independent Counters**: Each protocol maintains its own atomic counter
- **Server Identity**: Responses include pod/hostname for tracking load distribution
- **TCP Command Protocol**:
  - Send numeric value (e.g., `"5"`) → stays open N seconds
  - Send `"OPEN"` → persistent connection
  - Send anything else → immediate close

### Interactive Dashboard (port 9093)
- **Request Controls**: Send 1-100 concurrent requests with single click (HTTP, Pulse, Linger, Hold open)
- **Distribution Panel**: See request breakdown per server (e.g., "33, 33, 34" across 3 pods)
- **Stats API**: Server-side metrics with latency aggregates (min/max/avg/p50/p95/p99) via `/stats`
- **Distribution API**: Server-side tracking via `/api/distribution` for monitoring tools
- **Request History**: Last 20 requests with latency and server identity
- **Backend Configuration**: Switch between services (e.g., `getback`, `getback-canary`)
- **Persistent State**: Distribution and history data survives page reloads (localStorage)

### Operational
- **Zero Dependencies**: Python 3.11+ standard library only
- **Health Probes**: `/health` endpoint for Kubernetes liveness/readiness
- **Graceful Shutdown**: 5-second timeout for clean pod termination
- **Multi-cluster Ready**: Works with Skupper, Istio, Linkerd service meshes

## Dashboard Guide

The interactive dashboard (port 9093) is the main interface for demonstrating load balancing:

### Making Requests

1. **Set Amount**: 10 (default) - sends N concurrent requests per click
2. **Click buttons**:
   - `Send HTTP Requests` - fires Amount concurrent HTTP requests
   - `Pulse` - fires Amount concurrent TCP requests (immediate close)
   - `Linger (2s)` - TCP requests that stay open 2 seconds
   - `Hold open` - TCP requests that stay open indefinitely

### Distribution Panel

Shows aggregated request counts per server:

```
Request Distribution
────────────────────────────────────
getback-876777f64-dkrlv    34 requests  (34%)
getback-876777f64-kc6hw    33 requests  (33%)
getback-876777f64-kcszx    33 requests  (33%)
Total: 100 requests
```

**Key insights:**
- ✅ Even distribution (33%, 33%, 33%) = good load balancing
- ⚠️ Uneven (50%, 30%, 20%) = check session affinity or pod health
- ❌ Single server (100%, 0%, 0%) = session affinity enabled or service misconfigured

**Understanding the totals:**

The distribution panel shows **requests sent by the dashboard UI to backends** (client-side tracking):
- Tracked in browser localStorage (per-client view)
- Shows only requests made through UI buttons
- Total = sum of requests to all backend servers

This differs from `/stats` counters, which show **requests received by the dashboard container itself**:
- `http_counter`/`tcp_counter` = requests hitting the dashboard's own ports 9091/9092
- Useful when dashboard is deployed as a backend service (e.g., in Skupper multi-cluster)
- May exceed distribution totals if dashboard receives external traffic

**Example scenario:**
```
Distribution total: 15200 requests  ← Sent by dashboard UI to backends
/stats counters:     9903 requests  ← Received by dashboard container

Difference: Dashboard is both a client (sends 15200) and a server (receives 9903)
```

### Backend Configuration

Switch between services without reloading:

- **HTTP Backend**: `getback:9091` (default in Kubernetes)
- **TCP Backend**: `getback:9092`
- **Amount**: 10 (requests per click)

**Examples:**
- Test canary: Set HTTP to `getback-canary:9091`
- Test blue/green: Switch between `stable:9091` and `candidate:9091`
- Multi-cluster: Target `mkl-backend-http:9091` (Skupper listener)

Click **Save** to persist configuration to browser localStorage.

### Clear Data

- **Clear Distribution**: Reset server counts (useful when switching backends)
- **Clear History**: Reset request history

Data persists across page reloads via localStorage.

## API Reference

The dashboard server (port 9093) provides several JSON APIs for monitoring and control:

### Distribution Tracking API

**Server-side distribution tracking** - tracks request counts across backend servers/pods:

```bash
# Get current distribution
GET /api/distribution

# Response:
{
  "distribution": {
    "getback-876777f64-dkrlv": {"count": 34, "percent": 34.0},
    "getback-876777f64-kc6hw": {"count": 33, "percent": 33.0},
    "getback-876777f64-kcszx": {"count": 33, "percent": 33.0}
  },
  "total": 100,
  "timestamp": 1715812345
}

# Reset distribution counts
POST /api/distribution/reset

# Response:
{
  "message": "Distribution reset",
  "cleared": 100,
  "timestamp": 1715812345
}
```

**Key differences from client-side tracking:**
- **Server-side** (`/api/distribution`): Tracks all requests made through the dashboard, persists server-side in memory, survives page reloads, visible to all clients
- **Client-side** (distribution panel UI): Tracked in browser localStorage, per-client view, can diverge if multiple users

**Use cases:**
- Monitor load balancing from external tools (curl, scripts, monitoring systems)
- Aggregate distribution across multiple dashboard users
- Automate testing and validation of load balancer configuration

### Stats API

**Server-side metrics with latency aggregates** - tracks dashboard's own counters and backend request latencies:

```bash
# Get server stats with latency aggregates
GET /stats

# Response:
{
  "http_counter": 2453,
  "tcp_counter": 7450,
  "uptime": 1539,
  "timestamp": 1715812345,
  "latency": {
    "http": {
      "min": 2,
      "max": 45,
      "avg": 12,
      "p50": 10,
      "p95": 28,
      "p99": 38,
      "count": 1000
    },
    "tcp": {
      "min": 3,
      "max": 50,
      "avg": 15,
      "p50": 12,
      "p95": 30,
      "p99": 42,
      "count": 200
    }
  }
}
```

**Key fields:**
- `http_counter`/`tcp_counter`: Dashboard container's own HTTP/TCP counters (requests received by this instance)
- `latency.http`/`latency.tcp`: Aggregates from last 1000 backend requests sent by dashboard UI (min/max/avg/p50/p95/p99 in ms)
- `uptime`: Dashboard server uptime in seconds
- `count`: Number of latency samples tracked (max 1000 per protocol)

**Use cases:**
- Monitor dashboard latency to backends (network/service health)
- Track request rate (count vs. uptime)
- Detect latency spikes (p95/p99 monitoring)

### Request APIs (Dashboard UI)

```bash
# Make HTTP request to backend (used by dashboard UI)
POST /api/request/http
# Body: {"backend": "hostname:9091"}

# Make TCP request to backend (used by dashboard UI)
POST /api/request/tcp
# Body: {"command": "test", "backend": "hostname:9092"}
```

## Deployment Options

### 1. Local (Bare Metal)

```bash
python -m getback --http-port 9091 --tcp-port 9092
```

### 2. Docker

```bash
# Build local dev image
docker build -t getback:dev .

# Run locally (all ports)
docker run -p 9091:9091 -p 9092:9092 -p 9093:9093 getback:dev

# Open dashboard
open http://localhost:9093/

# Push to registry (for Skupper east/west deployments)
docker build -t quay.io/<namespace>/getback:latest .
docker push quay.io/<namespace>/getback:latest
```

### 3. Podman

```bash
# Build local dev image
podman build -t getback:dev .

# Run locally (all ports)
podman run -p 9091:9091 -p 9092:9092 -p 9093:9093 getback:dev

# Open dashboard
open http://localhost:9093/

# Push to registry (for Skupper east/west deployments)
# Authenticate once
podman login quay.io

# Push :latest tag (required for east/west deployments)
podman build -t quay.io/<namespace>/getback:latest .
podman push quay.io/<namespace>/getback:latest
```

### 4. Kubernetes (Skaffold)

```bash
# Development mode with live reload
skaffold dev

# Production deployment
skaffold run
```

Deploys 3 replicas for load balancing demonstration.

## Testing

### Local Development (Podman)

Quick local testing without Kubernetes:

```bash
# Build local dev image
podman build -t getback:dev .

# Run container (all ports)
podman run --rm -p 9091:9091 -p 9092:9092 -p 9093:9093 getback:dev

# Access dashboard
open http://localhost:9093/
```

For testing with Kubernetes manifests locally, use `podman kube play` (requires adjusting image reference in YAML to `getback:dev`).

### Single-Cluster Setup (Standard Kubernetes)

Test load balancing across 3 replicas in one cluster:

```bash
# Development mode with live reload
skaffold dev

# Or production mode
skaffold run

# Port-forward to dashboard
kubectl port-forward svc/getback 9093:9093

# Open browser
open http://localhost:9093/
```

**What to expect:**
- Dashboard shows request distribution across 3 replicas
- Example: "34, 33, 33 requests" across 3 pods
- Local code changes auto-reload with `skaffold dev`

### Multi-Cluster Setup (Skupper)

Test cross-cluster load balancing with two terminals:

**Terminal 1 (East cluster):**
```bash
# Set context to east namespace
kubectl config set-context --current --namespace=east

# Apply Skupper networking (skip deployment.yaml)
kubectl apply -f east/connectors.yaml

# Deploy with Skaffold (production mode)
skaffold run
```

**Terminal 2 (West cluster):**
```bash
# Set context to west namespace
kubectl config set-context --current --namespace=west

# Apply Skupper networking (skip deployment.yaml)
kubectl apply -f west/service.yaml
kubectl apply -f west/connectors.yaml
kubectl apply -f west/listeners.yaml

# Deploy with Skaffold (development mode with live reload)
skaffold dev
```

**Access the dashboard:**
```bash
# Port-forward to west dashboard (in a third terminal)
kubectl port-forward -n west svc/getback-dashboard 9093:9093

# Open browser
open http://localhost:9093/
```

**What to expect:**
- Dashboard shows request distribution across both east and west pods
- Example: "50 requests to east pod, 50 requests to west pod" (50/50 split)
- Skupper listeners aggregate traffic from both clusters
- Changes to west code auto-reload via `skaffold dev`

**Troubleshooting:**
```bash
# Check Skupper status
skupper status

# View pod logs (east)
kubectl logs -n east -l app=getback --tail=50 -f

# View pod logs (west)
kubectl logs -n west -l app=getback --tail=50 -f

# Check distribution API
curl http://localhost:9093/api/distribution | jq
```

## Use Cases

- **Load Balancing Demos**: Watch distribution panel show "10, 10, 10" across 3 replicas
- **Service Mesh Testing**: Verify Skupper/Istio/Linkerd traffic distribution
- **Multi-cluster Networking**: Test cross-cluster connectivity and latency
- **Blue/Green Deployments**: Switch backend targets in UI (e.g., `stable` vs `canary`)
- **Connection Modes**: Compare persistent vs. ephemeral TCP connection handling
- **Layer 4 vs Layer 7**: Demonstrate TCP vs HTTP load balancing differences
- **Kubernetes Training**: Interactive tool for teaching service discovery and load balancing
- **Performance Testing**: Send 100 concurrent requests with single click

## Documentation

- **[Quickstart Guide](specs/001-dual-counter/quickstart.md)** - Full usage guide, examples, troubleshooting
- **[HTTP Protocol](specs/001-dual-counter/contracts/http-protocol.md)** - HTTP API specification
- **[TCP Protocol](specs/001-dual-counter/contracts/tcp-protocol.md)** - TCP protocol specification
- **[Implementation Plan](specs/001-dual-counter/plan.md)** - Design decisions and architecture
- **[Data Model](specs/001-dual-counter/data-model.md)** - Entity definitions and state management

## Sample Clients

Pre-built clients in `clients/` directory:

```bash
# HTTP client
python clients/http_client.py http://localhost:9091

# TCP client - immediate close
python clients/tcp_client.py localhost 9092 test

# TCP client - 5 second connection
python clients/tcp_client.py localhost 9092 5

# TCP client - persistent connection
python clients/tcp_client.py localhost 9092 OPEN
```

## Load Balancer Example

Run 3 instances and test distribution:

```bash
# Start 3 instances (different ports)
python -m getback --http-port 9091 --tcp-port 9092 &
python -m getback --http-port 9191 --tcp-port 9192 &
python -m getback --http-port 9291 --tcp-port 9292 &

# Configure load balancer (HAProxy, nginx, etc.) to distribute across ports
# Make requests and observe counter patterns
```

Or use Kubernetes:

```bash
skaffold dev  # Deploys 3 pods with automatic load balancing
for i in {1..9}; do curl http://localhost:9091/; done
# Expected: 1,1,1,2,2,2,3,3,3 (round-robin across 3 pods)
```

## Configuration

**Command-line arguments**:
```bash
python -m getback \
  --http-port 8080 \
  --tcp-port 8090 \
  --dashboard-port 8093 \
  --host 0.0.0.0 \
  --log-level DEBUG
```

**Environment variables**:
```bash
export HTTP_PORT=8080
export TCP_PORT=8090
export DASHBOARD_PORT=8093
export LOG_LEVEL=INFO
export BACKEND_HOST=getback  # Dashboard targets this service (Kubernetes)
python -m getback
```

**Kubernetes environment** (set in `k8s/deployment.yaml`):
- `HTTP_PORT`: 9091
- `TCP_PORT`: 9092
- `DASHBOARD_PORT`: 9093
- `BACKEND_HOST`: `getback` (service name for load-balanced requests)
- `HOSTNAME`: Auto-set by Kubernetes to pod name

## Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=getback --cov-report=html
```

## Architecture

- **Language**: Python 3.11+
- **Concurrency**: asyncio (single event loop, concurrent servers)
- **Dependencies**: Standard library only (asyncio, logging)
- **Design Principles**: Simplicity first, clear boundaries, observable behavior

See [Constitution](\.specify/memory/constitution.md) for design principles.

## Project Structure

```
getback/
├── __main__.py           # Entry point with graceful shutdown
├── counter.py            # Atomic counter business logic
├── http_server.py        # HTTP protocol handler (port 9091)
├── tcp_server.py         # TCP protocol handler (port 9092)
├── dashboard_server.py   # Interactive console (port 9093)
├── config.py             # Configuration management
└── cli.py                # CLI argument parsing

k8s/                      # Standard Kubernetes deployment
├── deployment.yaml       # 3 replicas with Skaffold
└── service.yaml          # ClusterIP service

west/                     # Skupper multi-cluster (west site)
├── deployment.yaml       # 1 replica, quay.io image, namespace: west
├── service.yaml          # ClusterIP for dashboard (getback-dashboard:9093)
├── connectors.yaml       # Skupper connectors (HTTP/TCP)
└── listeners.yaml        # Skupper listeners (aggregates all sites)

east/                     # Skupper multi-cluster (east site)
├── deployment.yaml       # 1 replica, quay.io image, namespace: east
└── connectors.yaml       # Skupper connectors (HTTP/TCP)

clients/                  # Sample client implementations
tests/                    # Test suite
specs/                    # Design documentation (spec-driven development)
```

## Contributing

This is a demonstration tool built following spec-driven development practices. See `specs/001-dual-counter/` for complete specification and design documentation.

## License

Apache  License 2.0

## Credits

Built with [Spec-Kit](https://github.com/github/spec-kit) - Spec-driven development toolkit.
