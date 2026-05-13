# Skaffold Usage

This repo includes a `skaffold.yaml` for local Kubernetes development.

## Prerequisites

- Kubernetes cluster available in your current `kubectl` context
- `skaffold` installed
- Docker or another local image builder available to Skaffold

## Start Development Mode

Run:

```bash
skaffold dev
```

Skaffold will:

- build the `getback` image from the repo `Dockerfile`
- deploy [k8s/deployment.yaml](/home/paulwright/repos/sk/get-back/k8s/deployment.yaml:1)
- deploy [k8s/service.yaml](/home/paulwright/repos/sk/get-back/k8s/service.yaml:1)
- port-forward the service to your machine

## Local Ports

After `skaffold dev` is running, these ports are available locally:

- `9091` HTTP server
- `9092` TCP server
- `9093` dashboard

Examples:

```bash
curl http://localhost:9091/
curl http://localhost:9091/health
echo "test" | nc localhost 9092
open http://localhost:9093
```

## What Happens When You Edit Code

The `dev` profile in [skaffold.yaml](/home/paulwright/repos/sk/get-back/skaffold.yaml:1) syncs:

```text
getback/**/*.py
```

That means Python source changes in `getback/` are copied into the running container during `skaffold dev`.

Important limits:

- Sync is not full hot reload.
- If the running process does not restart, synced Python changes may not take effect immediately.
- Changes outside `getback/**/*.py` usually require rebuild and redeploy.

## When Rebuild or Redeploy Is Needed

Expect a rebuild/redeploy for changes to:

- `pyproject.toml`
- `requirements.txt`
- `skaffold.yaml`
- files under `k8s/`
- `Dockerfile`

## One-Off Deploy

For a non-interactive deploy:

```bash
skaffold run
```

## Cleanup

To stop the dev session, press `Ctrl+C` in the terminal running `skaffold dev`.

To remove deployed resources:

```bash
skaffold delete
```
