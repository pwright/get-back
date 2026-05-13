# Web Testing Console Design

**Port**: 9093  
**Purpose**: Interactive testing interface for load balancing demonstration  
**Date**: 2026-05-13

## Overview

The web testing console provides a self-contained interface for demonstrating and testing the dual-protocol counter service. Unlike traditional dashboards that only display metrics, this console is both **observer** (displays counters) and **actor** (makes requests).

## Core Principle: Self-Contained Demo Tool

**Problem**: Demonstrating load balancing requires:
1. Running multiple backend instances
2. Writing client code to make requests
3. Observing response distribution
4. Tracking which backend served each request

**Solution**: Console eliminates steps 2-4 by providing:
- One-click request buttons (no client code needed)
- Visual request/response history
- Server identity in every response
- Real-time counter updates

## Architecture

### Dual Role Design

```
Console (Port 9093)
├── HTTP Server (receives browser requests)
│   ├── GET / → Serve HTML/JS UI
│   ├── GET /stats → JSON stats API
│   ├── POST /api/request/http → Trigger HTTP request to 9091
│   └── POST /api/request/tcp → Trigger TCP request to 9092
│
└── HTTP/TCP Client (makes test requests)
    ├── → localhost:9091 (HTTP counter)
    └── → localhost:9092 (TCP counter)
```

### Request Flow

**User Action**: Click "Make HTTP Request" button in browser

**Flow**:
1. Browser → POST /api/request/http (to console on 9093)
2. Console → GET / (to HTTP server on 9091)
3. HTTP server responds: `{"counter": 42, "server": "pod-abc"}`
4. Console stores in history
5. Console → JSON response to browser
6. Browser updates history panel

**Result**: User sees request appear in history with server identity visible

## UI Components

### 1. Counter Display (Existing)

Real-time display of current counter values:
- HTTP counter (updates every 1s)
- TCP counter (updates every 1s)
- Uptime
- Total requests

### 2. Request Panel (New)

Interactive controls:
```
┌─────────────────────────────┐
│ Make Test Requests          │
├─────────────────────────────┤
│ [HTTP Request]  [TCP: 5s]   │
│ [TCP: OPEN]     [TCP: test] │
└─────────────────────────────┘
```

Buttons:
- **HTTP Request**: Makes GET request to 9091
- **TCP: 5s**: Makes TCP request with "5" command
- **TCP: OPEN**: Makes TCP request with "OPEN" command
- **TCP: test**: Makes TCP request with "test" command

### 3. Request History Panel (New)

Scrollable list of recent requests:
```
┌──────────────────────────────────────────┐
│ Request History                          │
├──────────────────────────────────────────┤
│ 12:34:56  HTTP  → 42 (pod-abc)  ✓ 12ms  │
│ 12:34:55  TCP   → 15 (pod-def)  ✓ 3001ms│
│ 12:34:53  HTTP  → 41 (pod-abc)  ✓ 8ms   │
│ 12:34:52  HTTP  → 40 (pod-ghi)  ✓ 10ms  │
└──────────────────────────────────────────┘
```

Each entry shows:
- Timestamp
- Protocol (HTTP/TCP)
- Counter value received
- **Server identity** (which backend responded)
- Status (✓ success, ✗ error)
- Latency

### 4. Distribution Panel (Core)

Shows aggregated request counts per server:
```
┌──────────────────────────────────┐
│ Request Distribution             │
├──────────────────────────────────┤
│ pod-abc    8 requests   (33%)    │
│ pod-def    8 requests   (33%)    │
│ pod-ghi    8 requests   (33%)    │
│ Total: 24 requests               │
└──────────────────────────────────┘
```

**Why Core**: For load balancing demos, this is essential. Seeing "8, 8, 8" proves round-robin at a glance. History panel shows individual requests (good for debugging), distribution panel shows the pattern (good for demos).

**Implementation**: Client-side JavaScript tracks requests in memory:
```javascript
const serverCounts = {};
serverCounts[server] = (serverCounts[server] || 0) + 1;
```

**Display**: Simple list with counts and percentages. Optional future: bar chart visualization.

## API Endpoints

### GET /
Serves HTML UI with embedded JavaScript.

### GET /stats
Returns JSON stats (existing):
```json
{
  "http_counter": 42,
  "tcp_counter": 15,
  "uptime": 3600,
  "timestamp": 1715612345
}
```

### POST /api/request/http
Triggers HTTP request to port 9091.

**Request**: `{}`

**Response**:
```json
{
  "counter": 42,
  "server": "getback-7d4f8c6b9-abc12",
  "latency_ms": 12,
  "timestamp": 1715612345
}
```

### POST /api/request/tcp
Triggers TCP request to port 9092.

**Request**:
```json
{
  "command": "5"  // or "OPEN", "test", etc.
}
```

**Response**:
```json
{
  "counter": 15,
  "server": "getback-7d4f8c6b9-def45",
  "latency_ms": 3001,
  "command": "5",
  "timestamp": 1715612345
}
```

## Server Identity Implementation

### Option A: Hostname (RECOMMENDED)

```python
import os
import socket

server_id = os.environ.get("HOSTNAME", socket.gethostname())
```

**Kubernetes**: `HOSTNAME` env var = pod name (e.g., `getback-7d4f8c6b9-abc12`)  
**Bare metal**: Falls back to `socket.gethostname()` (e.g., `laptop.local`)

**Why this works**:
- Kubernetes automatically sets HOSTNAME to pod name
- No additional dependencies
- Stable across pod lifecycle
- Human-readable in logs

### Response Format Changes

**HTTP responses** (plain text, backward compatible):
```
Before: 42
After:  42 (getback-7d4f8c6b9-abc12)
```

**TCP responses** (plain text, backward compatible):
```
Before: 15
After:  15 (getback-7d4f8c6b9-abc12)
```

**JSON format** (for console API):
```json
{
  "counter": 42,
  "server": "getback-7d4f8c6b9-abc12"
}
```

## Implementation Phases

### Phase 1: Server Identity (Quick Win)
- Add `server_id` to config
- Update HTTP/TCP response formats to include server identity
- Update existing dashboard to display server info
- **Estimated**: 1 hour

### Phase 2: Request API Endpoints
- Add POST /api/request/http endpoint
- Add POST /api/request/tcp endpoint
- Implement HTTP client (urllib)
- Implement TCP client (socket)
- **Estimated**: 2 hours

### Phase 3: Interactive UI
- Add request buttons to HTML
- Add history panel to HTML (individual requests with timestamps)
- Add distribution panel to HTML (aggregated counts per server)
- JavaScript to call request APIs and track server counts
- Display history with timestamps and server identity
- Display distribution with counts and percentages
- **Estimated**: 2.5 hours (includes distribution tracking)

### Phase 4: Polish
- Add latency tracking
- Add error handling (show ✗ for failed requests)
- Add clear history button
- Add auto-scroll for history
- **Estimated**: 1 hour

**Total Estimated Time**: 6.5 hours

## Use Cases

### Use Case 1: Quick Load Balancing Demo

**Scenario**: Demonstrating round-robin to stakeholders

**Steps**:
1. Deploy 3 replicas: `skaffold dev`
2. Open console: http://localhost:9093/
3. Click "HTTP Request" button 9 times
4. Point to distribution panel: "See? 3, 3, 3 - perfect round-robin!"
5. (Optional) Scroll history panel: "Here's every individual request"

**Time**: < 1 minute  
**No code needed**: Everything via UI  
**Visual proof**: Distribution panel shows exact balance

### Use Case 2: Persistent Connection Testing

**Scenario**: Showing least-connections load balancing

**Steps**:
1. Click "TCP: OPEN" 3 times (one per backend)
2. Click "HTTP Request" 6 times
3. Show history: TCP connections still open on each backend
4. Show HTTP requests distributed evenly despite persistent TCP

**Insight**: Least-connections works independently per protocol

### Use Case 3: Failure Detection

**Scenario**: Pod crashes during demo

**Steps**:
1. Making requests via console
2. History shows: pod-abc, pod-def, pod-ghi pattern
3. Kill pod-abc: `kubectl delete pod getback-...-abc`
4. Continue making requests
5. History now shows: pod-def, pod-ghi, pod-def, pod-ghi
6. **Visible immediately**: pod-abc stopped appearing

### Use Case 4: Development/Debugging

**Scenario**: Developer testing new backend behavior

**Steps**:
1. Run backend locally: `python -m getback`
2. Open console: http://localhost:9093/
3. Click buttons, observe responses
4. Change code, restart
5. Click buttons again, see new behavior

**Benefit**: No need to write curl commands or client scripts

## Comparison to Traditional Approach

### Without Console

```bash
# Terminal 1: Start server
python -m getback

# Terminal 2: Make requests manually
curl http://localhost:9091/
curl http://localhost:9091/
echo "test" | nc localhost 9092

# Terminal 3: Track results in spreadsheet
# Time: 12:34:56, Protocol: HTTP, Server: ???, Counter: 1
```

**Pain points**:
- Manual request execution
- Can't see server identity easily
- Hard to track patterns
- Requires command-line knowledge

### With Console

```
1. Open browser: http://localhost:9093/
2. Click buttons
3. Watch history panel update
```

**Benefits**:
- Point-and-click interface
- Server identity visible immediately
- Pattern recognition automatic (see distribution)
- Accessible to non-technical stakeholders

## Security Considerations

**Not for Production**: This is a demonstration/testing tool.

**Risks**:
- Console can make unlimited requests (no rate limiting)
- No authentication
- Runs on 0.0.0.0 by default

**Mitigations**:
- Document as "demo tool only"
- Add warning in UI
- Consider --console-enable flag (disabled by default for prod)

## Alternatives Considered

### Alternative 1: Separate Frontend App

Like Apache Skupper Router Console - separate React/Vue app.

**Rejected because**:
- Adds build complexity (npm, webpack, etc.)
- Requires dependencies (violates constitution)
- Harder to deploy (two containers)

### Alternative 2: CLI-Only (No Console)

Rely on curl/nc for testing.

**Rejected because**:
- Not accessible to non-technical users
- Hard to demonstrate visually
- Requires documentation/training

### Alternative 3: Prometheus + Grafana

Use /metrics endpoint + external Grafana dashboard.

**Rejected because**:
- Doesn't solve "making requests" problem
- Heavy infrastructure (violates simplicity)
- Can't easily show per-request server identity

### Selected: Embedded Console

Self-contained HTML/JS in Python string, stdlib HTTP client.

**Why**:
- Zero additional dependencies
- Single deployment (one container)
- Accessible via browser
- Can both observe AND act
- Aligns with constitution (simplicity first)

## Future Enhancements (Post-MVP)

- **Request rate control**: Slider for "make N requests per second"
- **Bulk testing**: "Make 100 requests" button
- **Export history**: Download CSV of request history
- **WebSocket updates**: Real-time counter push (instead of polling)
- **Filter history**: Show only HTTP or only TCP
- **Visual bar chart**: Graphical bars instead of just counts in distribution panel
- **Custom TCP commands**: Text input for arbitrary commands
- **Connection pooling**: Reuse TCP OPEN connections
- **Clear distribution button**: Reset aggregated counts
- **Per-protocol distribution**: Separate HTTP and TCP distribution panels

## Success Criteria

Console is successful when:

1. **No client code needed**: Entire demo done via browser
2. **Server identity visible**: Can see which backend served each request within 1 second
3. **Pattern recognition**: Round-robin, least-connections patterns obvious from history
4. **Accessible**: Non-technical stakeholder can run demo independently
5. **Simple**: Zero external dependencies, pure stdlib
