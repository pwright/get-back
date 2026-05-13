# Kubernetes Manifests for Get-Back

Kubernetes deployment files for the Get-Back dual-protocol counter service.

## Server Manifests

### deployment.yaml
Deploys 3 replicas of the Get-Back server with:
- HTTP endpoint on port 9091
- TCP endpoint on port 9092
- Health probes (liveness and readiness)
- Resource limits

### service.yaml
LoadBalancer service exposing both ports:
- HTTP: 9091
- TCP: 9092
- No session affinity (demonstrates load balancing)

## Client Manifests

### client-http-job.yaml
**One-off HTTP test job**

Runs 10 HTTP requests and exits.

**Usage**:
```bash
kubectl apply -f k8s/client-http-job.yaml
kubectl logs job/http-client-test -f
kubectl delete job http-client-test
```

**Expected Output**:
```
Running HTTP client test...
Counter: 1
Counter: 2
Counter: 3
...
Counter: 10
HTTP test complete!
```

### client-tcp-job.yaml
**One-off TCP test job**

Tests all three TCP command types:
- Immediate close
- 3-second connection
- 5-second connection

**Usage**:
```bash
kubectl apply -f k8s/client-tcp-job.yaml
kubectl logs job/tcp-client-test -f
kubectl delete job tcp-client-test
```

### client-load-generator.yaml
**Continuous load generation**

Deploys 2 pods, each running:
- HTTP client (1 request every 2 seconds)
- TCP client (mixed commands every few seconds)

**Usage**:
```bash
# Start load generator
kubectl apply -f k8s/client-load-generator.yaml

# Watch server logs to see load distribution
kubectl logs -l app=getback --tail=20 -f

# Scale load
kubectl scale deployment load-generator --replicas=5

# Stop load
kubectl delete deployment load-generator
```

**Use Cases**:
- Demonstrate round-robin load balancing (watch counter progression)
- Stress test server under sustained load
- Observe pod scaling behavior

### client-cronjob.yaml
**Periodic health checks**

Runs every 5 minutes to:
1. Check `/health` endpoint
2. Verify HTTP counter works
3. Verify TCP endpoint works

**Usage**:
```bash
# Deploy CronJob
kubectl apply -f k8s/client-cronjob.yaml

# Watch for job executions
kubectl get jobs --watch

# View health check logs
kubectl logs -l type=health-check --tail=50

# Manually trigger a run
kubectl create job --from=cronjob/periodic-health-check manual-check

# Delete CronJob
kubectl delete cronjob periodic-health-check
```

## Complete Deployment

Deploy everything (server + clients):

```bash
# Server
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Wait for server to be ready
kubectl wait --for=condition=available deployment/getback --timeout=60s

# Run one-off tests
kubectl apply -f k8s/client-http-job.yaml
kubectl apply -f k8s/client-tcp-job.yaml

# Watch job logs
kubectl logs job/http-client-test -f
kubectl logs job/tcp-client-test -f

# Start continuous load (optional)
kubectl apply -f k8s/client-load-generator.yaml

# Deploy periodic health checks (optional)
kubectl apply -f k8s/client-cronjob.yaml
```

## Observing Load Balancing

### Watch Server Logs

```bash
# All pods
kubectl logs -l app=getback --tail=10 -f

# Specific pod
kubectl logs getback-7d4f8c6b9-abc12 -f
```

With load generator running, you'll see:
```
2026-05-13 12:34:56 [INFO] getback.http: HTTP counter: 42
2026-05-13 12:34:56 [INFO] getback.tcp: TCP counter: 15 (mode: timed)
2026-05-13 12:34:57 [INFO] getback.http: HTTP counter: 43
```

Each pod has independent counters, so distribution is visible.

### Check Counter Distribution

```bash
# Get all pod names
kubectl get pods -l app=getback -o name

# Check HTTP counter on each pod
for pod in $(kubectl get pods -l app=getback -o name); do
  echo "$pod:"
  kubectl logs $pod | grep "HTTP counter" | tail -1
done
```

Expected pattern with 3 pods and round-robin:
```
pod/getback-...-abc: HTTP counter: 34
pod/getback-...-def: HTTP counter: 33
pod/getback-...-ghi: HTTP counter: 34
```

## Cleanup

```bash
# Delete client resources
kubectl delete job http-client-test tcp-client-test --ignore-not-found
kubectl delete deployment load-generator --ignore-not-found
kubectl delete cronjob periodic-health-check --ignore-not-found

# Delete server
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/service.yaml

# Or delete everything at once
kubectl delete all -l app=getback
kubectl delete all -l app=getback-client
kubectl delete all -l app=load-generator
```

## Skaffold Integration

The main `skaffold.yaml` deploys only the server. To include clients:

**Quick test after deployment**:
```bash
# Start server
skaffold dev

# In another terminal, run client jobs
kubectl apply -f k8s/client-http-job.yaml
kubectl logs job/http-client-test -f
```

**Continuous load testing**:
```bash
# Deploy server
skaffold run

# Deploy load generator
kubectl apply -f k8s/client-load-generator.yaml

# Watch both server and client logs
kubectl logs -l app=getback -f --prefix &
kubectl logs -l app=load-generator -f --prefix
```

## Advanced Scenarios

### Scenario 1: Burst Load Test

```bash
# Deploy 10 parallel HTTP test jobs
for i in {1..10}; do
  kubectl create job http-burst-$i --image=getback -- \
    sh -c "for j in {1..5}; do python clients/http_client.py http://getback:9091/; done"
done

# Watch all jobs complete
kubectl get jobs --watch

# See total requests across all pods
kubectl logs -l app=getback | grep "HTTP counter" | wc -l
```

### Scenario 2: TCP Persistent Connection Test

Create a job that opens OPEN connections:

```bash
kubectl create job tcp-persistent --image=getback -- \
  sh -c "python clients/tcp_client.py getback 9092 OPEN"

# Connection stays open - check server logs
kubectl logs -l app=getback | grep "mode: persistent"

# Delete job to close connection
kubectl delete job tcp-persistent
```

### Scenario 3: Mixed Protocol Load

Use load generator with custom ratios:

```yaml
# Edit client-load-generator.yaml
# Adjust sleep times to change request rate
# HTTP: sleep 1  (1 req/sec)
# TCP:  sleep 5  (0.2 req/sec)
```

## Troubleshooting

**Jobs stuck in Pending**:
```bash
kubectl describe pod -l app=getback-client
# Check Events section for issues
```

**Can't reach service**:
```bash
# Verify service endpoints
kubectl get endpoints getback

# Should show 3 pod IPs with ports 9091,9092
```

**Load not distributing**:
```bash
# Check service has no session affinity
kubectl get service getback -o yaml | grep sessionAffinity
# Should be: sessionAffinity: None
```

**Client connection refused**:
```bash
# Verify server pods are ready
kubectl get pods -l app=getback

# All should show 1/1 READY
# If not, check server logs for errors
```
