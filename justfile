# Get-Back justfile - Common build, push, and deployment tasks
# Usage: just <recipe>

# Default recipe (show help)
default:
    @just --list

# Variables
image_repo := env_var_or_default('IMAGE_REPO', 'quay.io/pwright/getback')
git_sha := `git rev-parse --short HEAD`
git_tag := `git describe --tags --always`

# === Local Development ===

# Run locally with default ports
run:
    python -m getback

# Run with debug logging
debug:
    python -m getback --log-level DEBUG

# Run tests
test:
    pytest

# Run tests with coverage
test-cov:
    pytest --cov=getback --cov-report=html --cov-report=term

# Install development dependencies
install:
    pip install -r requirements-dev.txt
    pip install -e .

# === Container Images ===

# Build container image with git SHA tag
build:
    podman build -t {{image_repo}}:{{git_sha}} .

# Build and tag as latest
build-latest:
    podman build -t {{image_repo}}:{{git_sha}} -t {{image_repo}}:latest .

# Push image with SHA tag
push: build
    podman push {{image_repo}}:{{git_sha}}

# Push both SHA and latest tags
push-latest: build-latest
    podman push {{image_repo}}:{{git_sha}}
    podman push {{image_repo}}:latest

# Build and push in one command
release: build-latest
    podman push {{image_repo}}:{{git_sha}}
    podman push {{image_repo}}:latest
    @echo "Released: {{image_repo}}:{{git_sha}} and latest"

# === Kubernetes (Standard) ===

# Deploy to Kubernetes with Skaffold
deploy:
    skaffold run

# Development mode (live reload)
dev:
    skaffold dev

# Delete Kubernetes deployment
delete:
    kubectl delete -f k8s/deployment.yaml -f k8s/service.yaml

# Port-forward to dashboard
forward:
    kubectl port-forward svc/getback 9093:9093

# Get pod logs
logs:
    kubectl logs -l app=getback --tail=100 -f

# Watch pods
watch:
    kubectl get pods -l app=getback -w

# === Skupper Multi-Cluster ===

# Deploy to west cluster
deploy-west:
    kubectl apply -f west/deployment.yaml
    kubectl apply -f west/service.yaml
    kubectl apply -f west/connectors.yaml
    kubectl apply -f west/listeners.yaml

# Deploy to east cluster
deploy-east:
    kubectl apply -f east/deployment.yaml
    kubectl apply -f east/connectors.yaml

# Delete west deployment
delete-west:
    kubectl delete -f west/

# Delete east deployment
delete-east:
    kubectl delete -f east/

# Port-forward to west dashboard
forward-west:
    kubectl port-forward -n west svc/getback-dashboard 9093:9093

# Port-forward to east dashboard (requires east service - see README)
forward-east:
    @echo "Note: east/ doesn't have a service.yaml - create one or port-forward to pod"
    kubectl port-forward -n east deployment/getback 9093:9093

# === Testing & Debugging ===

# Make HTTP request
test-http:
    curl http://localhost:9091/

# Make TCP request
test-tcp:
    echo "test" | nc localhost 9092

# Open dashboard in browser
open:
    open http://localhost:9093/

# Check health endpoint
health:
    curl http://localhost:9091/health

# Get stats from dashboard
stats:
    curl -s http://localhost:9093/stats | python -m json.tool

# === Load Testing ===

# Send N HTTP requests (default: 10)
load-http n="10":
    for i in {1..{{n}}}; do curl -s http://localhost:9091/; done

# Send N concurrent HTTP requests
load-http-concurrent n="10":
    seq {{n}} | xargs -P{{n}} -I{} curl -s http://localhost:9091/

# === Cleanup ===

# Clean Python cache files
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf .pytest_cache htmlcov .coverage

# Clean everything (cache + test artifacts)
clean-all: clean
    rm -rf build/ dist/ *.egg-info/

# === Image Management ===

# List local images
images:
    podman images | grep getback

# Remove local images
rmi:
    podman rmi {{image_repo}}:{{git_sha}} {{image_repo}}:latest || true

# Pull latest image
pull:
    podman pull {{image_repo}}:latest

# === Documentation ===

# View quickstart guide
quickstart:
    cat specs/001-dual-counter/quickstart.md

# View HTTP protocol spec
http-spec:
    cat specs/001-dual-counter/contracts/http-protocol.md

# View TCP protocol spec
tcp-spec:
    cat specs/001-dual-counter/contracts/tcp-protocol.md
