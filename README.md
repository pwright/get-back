# Get-Back: Dual-Protocol Counter Service

A simple network service exposing incrementing counters via HTTP and TCP protocols. Designed for demonstrating and testing load balancer behavior.

Dashboard: 9093
TCP: 9092
HTTP: 9091

## Quick Start Skupper

```bash
# Deploy the app into each site namespace
kubectl apply -f east/deployment.yaml
kubectl apply -f west/deployment.yaml

# Apply Skupper connector/listener resources
kubectl apply -f east/connectors.yaml
kubectl apply -f west/connectors.yaml
kubectl apply -f west/listeners.yaml
```

Expose west/getback 9091 so you can access dashboard

Create some traffic and observe the balancing

![alt text](image-1.png)



The deployment manifests use `quay.io/pwright/getback:latest`, so push that tag before applying them.

## Quick Start local

```bash
# Run locally
python -m getback

# Test HTTP endpoint
curl http://localhost:9091/  # Returns: 1, 2, 3...

# Test TCP endpoint
echo "test" | nc localhost 9092  # Returns: 1, 2, 3...
```

## Features

- **Dual Protocol**: HTTP (port 9091) and TCP (port 9092)
- **Independent Counters**: Each protocol maintains its own atomic counter
- **TCP Command Protocol**:
  - Send numeric value (e.g., `"5"`) → stays open N seconds
  - Send `"OPEN"` → persistent connection
  - Send anything else → immediate close
- **Zero Dependencies**: Python 3.11+ standard library only
- **Load Balancer Testing**: Perfect for demonstrating round-robin, least-connections, etc.

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

- Verify load balancer round-robin distribution
- Test persistent vs. ephemeral TCP connection handling
- Demonstrate Layer 4 (TCP) vs. Layer 7 (HTTP) load balancing
- Quick network connectivity testing
- Learn asyncio concurrent server programming

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
  --host 0.0.0.0 \
  --log-level DEBUG
```

**Environment variables**:
```bash
export HTTP_PORT=8080 TCP_PORT=8090 LOG_LEVEL=INFO
python -m getback
```

**Kubernetes** (via `k8s/deployment.yaml` env section)

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
getback/              # Main package
├── counter.py        # Counter business logic
├── http_server.py    # HTTP protocol handler
├── tcp_server.py     # TCP protocol handler
├── config.py         # Configuration management
└── cli.py            # CLI argument parsing

clients/              # Sample client implementations
tests/                # Test suite
k8s/                  # Kubernetes manifests
specs/                # Design documentation
```

## Contributing

This is a demonstration tool built following spec-driven development practices. See `specs/001-dual-counter/` for complete specification and design documentation.

## License

[Add your license here]

## Credits

Built with [Spec-Kit](https://github.com/github/spec-kit) - Spec-driven development toolkit.
