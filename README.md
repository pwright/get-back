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
kubectl apply -f east/service.yaml      # ← Local service access
kubectl apply -f east/connectors.yaml   # ← Expose to Skupper network

# Access the console
kubectl port-forward -n west svc/getback 9093:9093
# Open http://localhost:9093/
```

**Directory structure:**
```
west/
├── deployment.yaml    # 1 replica, quay.io image
├── service.yaml       # ClusterIP service (local access)
├── connectors.yaml    # Skupper connectors (expose to network)
└── listeners.yaml     # Skupper listeners (aggregate sites)

east/
├── deployment.yaml
├── service.yaml
└── connectors.yaml
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
- **Real-time Metrics**: HTTP counter, TCP counter, uptime, total requests
- **Request Controls**: Send 1-100 concurrent requests with single click
- **Distribution Panel**: See request breakdown per server (e.g., "33, 33, 34" across 3 pods)
- **Request History**: Last 20 requests with latency and server identity
- **Backend Configuration**: Switch between services (e.g., `getback`, `getback-canary`)
- **Persistent State**: Distribution data survives page reloads (localStorage)

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
   - `Send HTTP Request` - fires Amount concurrent HTTP requests
   - `Immediate (test)` - fires Amount concurrent TCP requests (immediate close)
   - `Timed (2s)` - TCP requests that stay open 2 seconds
   - `Persistent (OPEN)` - TCP requests that stay open indefinitely

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

## Deployment Options

### 1. Local (Bare Metal)

```bash
python -m getback --http-port 9091 --tcp-port 9092
```

### 2. Docker

```bash
docker build -t getback .
docker run -p 9091:9091 -p 9092:9092 getback
```

### 3. Podman + Quay

```bash
# Authenticate once
podman login quay.io

# Build and push with the current git SHA as the tag
./scripts/podman-build-push.sh quay.io/<namespace>/getback

# Optionally also push a stable tag
EXTRA_TAG=latest ./scripts/podman-build-push.sh quay.io/<namespace>/getback
```

### 4. Kubernetes (Skaffold)

```bash
# Development mode with live reload
skaffold dev

# Production deployment
skaffold run
```

Deploys 3 replicas for load balancing demonstration.

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
├── deployment.yaml       # 1 replica, quay.io image
├── service.yaml          # ClusterIP service
├── connectors.yaml       # Skupper connectors
└── listeners.yaml        # Skupper listeners (aggregates all sites)

east/                     # Skupper multi-cluster (east site)
├── deployment.yaml
├── service.yaml
└── connectors.yaml

clients/                  # Sample client implementations
tests/                    # Test suite
specs/                    # Design documentation (spec-driven development)
```

## Contributing

This is a demonstration tool built following spec-driven development practices. See `specs/001-dual-counter/` for complete specification and design documentation.

## License

[Add your license here]

## Credits

Built with [Spec-Kit](https://github.com/github/spec-kit) - Spec-driven development toolkit.
