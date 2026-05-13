# Feature Specification: Dual-Protocol Counter Service

**Feature Branch**: `001-dual-counter`

**Created**: 2026-05-13

**Status**: Draft

**Input**: User description: "HTTP and TCP counter service for load balancing demonstration. HTTP GET on port 9091 returns incremental numbers (1, 2, 3...). TCP on port 9092 does similar but protocol/timing details to be determined."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - HTTP Counter Access (Priority: P1)

A load balancer operator or developer wants to verify that requests are being distributed across multiple server instances by observing unique sequential counters.

**Why this priority**: This is the core value proposition - HTTP endpoints are universally accessible and provide immediate visual feedback for load balancing verification. This represents the minimum viable demonstration.

**Independent Test**: Can be fully tested by sending HTTP GET requests to port 9091 and verifying that each response contains an incrementing integer. Delivers immediate value as a standalone service without requiring TCP client development.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** a client sends `GET /` to port 9091, **Then** the server responds with `1` (first request)
2. **Given** the server has responded to one request, **When** a second client sends `GET /` to port 9091, **Then** the server responds with `2`
3. **Given** the server is running, **When** multiple clients send concurrent requests to port 9091, **Then** each receives a unique sequential number with no duplicates or gaps
4. **Given** the server is running, **When** a client requests from any path (e.g., `/anything`), **Then** the server increments the counter and returns the next number

---

### User Story 2 - TCP Counter Access (Priority: P2)

A network engineer or developer wants to test TCP load balancing behavior using a simple counter-based protocol.

**Why this priority**: Adds TCP protocol support to demonstrate Layer 4 load balancing. Requires client implementation but extends the tool's utility to lower-level networking scenarios.

**Independent Test**: Can be tested independently with a TCP client (e.g., `telnet`, `nc`, or custom client) sending different command types. Delivers value by enabling TCP-level load balancer testing with variable connection lifetimes.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** a TCP client connects to port 9092 and sends a number (e.g., `"5"`), **Then** the server responds with the TCP counter value and keeps the connection open for that many seconds before closing
2. **Given** the server is running, **When** a TCP client connects and sends `"OPEN"`, **Then** the server responds with the TCP counter value and keeps the connection open indefinitely (until client closes or timeout)
3. **Given** the server is running, **When** a TCP client connects and sends any other text (e.g., `"hello"`), **Then** the server responds with the TCP counter value and immediately closes the connection
4. **Given** the TCP endpoint has served N requests, **When** a new TCP client connects, **Then** the TCP counter continues from N+1 (independent of HTTP counter)
5. **Given** the server is running, **When** multiple TCP clients connect simultaneously, **Then** each receives a unique sequential number from the TCP counter

---

### User Story 3 - Interactive Testing Console (Priority: P2)

An operator or tester wants to interact with the service through a web UI to observe load balancing behavior and make test requests.

**Why this priority**: Core to the demonstration purpose - enables interactive testing without writing client code. Essential for showcasing load balancing distribution patterns.

**Independent Test**: Can be tested by opening web console, clicking request buttons, and verifying request history is tracked with server identity visible.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** an operator opens the web console at port 9093, **Then** they see real-time counter values updating
2. **Given** the console is open, **When** the operator clicks "Make HTTP Request", **Then** the HTTP counter increments and response shows which server handled it
3. **Given** the console is open, **When** the operator clicks "Make TCP Request", **Then** the TCP counter increments and response shows server identity
4. **Given** multiple requests have been made, **When** the operator views the history panel, **Then** they see timestamped request/response pairs with server identities
5. **Given** multiple backend instances are running, **When** the operator makes 10 requests via console, **Then** they observe distribution pattern across backends

---

### User Story 4 - Service Observability (Priority: P3)

An operator wants to monitor the health and activity of the counter service via logs and health endpoints.

**Why this priority**: Enhances operational usability but isn't essential for the core demonstration purpose. Nice-to-have for production-like deployments.

**Independent Test**: Can be tested by checking logs and/or a health endpoint to verify service status without actually incrementing counters.

**Acceptance Scenarios**:

1. **Given** the server is running, **When** an operator checks the service, **Then** they can verify all ports are listening and accepting connections
2. **Given** requests are being processed, **When** an operator reviews logs, **Then** they see connection events and counter increments logged with server identity

---

### Edge Cases

- What happens when the counter reaches maximum integer value? (Assumption: Counter wraps to 1 or system is restarted before this occurs in practice)
- How does the system handle a client connection that opens but never sends data? (Assumption: TCP connections timeout after standard TCP keepalive period)
- What happens when the server is restarted? (Assumption: Counter resets to 1 - no persistence required for demonstration purposes)
- What happens if HTTP clients send POST, PUT, or other methods? (Assumption: All HTTP requests increment counter regardless of method)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose an HTTP endpoint on port 9091 (configurable)
- **FR-002**: System MUST expose a TCP endpoint on port 9092 (configurable)
- **FR-003**: System MUST maintain two separate counters (one for HTTP, one for TCP) that each increment atomically for their respective protocol requests
- **FR-004**: HTTP endpoint MUST respond to GET requests with the current counter value as plain text
- **FR-005**: HTTP endpoint MUST increment the counter for each request received
- **FR-006**: TCP endpoint MUST implement a command-based protocol where client input controls connection lifetime (numeric value = seconds to stay open, "OPEN" = indefinite, other = immediate close)
- **FR-007**: System MUST handle concurrent connections without counter collisions (no duplicate or skipped numbers)
- **FR-008**: Both servers MUST run concurrently in the same process
- **FR-009**: System MUST support graceful shutdown that cleanly closes both ports
- **FR-010**: System MUST log connection events (accepted, closed) and counter increments at appropriate log levels
- **FR-013**: Sample client implementations MUST be provided for both HTTP and TCP protocols to demonstrate usage
- **FR-014**: HTTP endpoint MUST provide a `/health` endpoint for liveness/readiness probes (returns 200 OK without incrementing counter)
- **FR-015**: System MUST provide a web testing console on port 9093 with:
  - Real-time counter visualization (auto-refresh)
  - JSON stats API endpoint (`/stats`)
  - Interactive request interface (UI buttons to trigger HTTP/TCP requests)
  - Request/response history tracking with timestamps
  - Server identity displayed in all responses (hostname/pod name)
- **FR-016**: All counter responses (HTTP and TCP) MUST include server identity to enable load balancing observation
- **FR-011**: Port numbers MUST be configurable via environment variables or command-line flags
- **FR-012**: System MUST maintain separate counters for HTTP and TCP protocols (HTTP counter and TCP counter increment independently)

### Key Entities

- **HTTP Counter**: An integer value that increments atomically for each HTTP request. Starts at 1 when the server starts. Independent of TCP counter.
- **TCP Counter**: An integer value that increments atomically for each TCP connection. Starts at 1 when the server starts. Independent of HTTP counter.
- **TCP Connection**: A stateful TCP socket connection with variable lifetime based on client command (numeric seconds, "OPEN" for persistent, or other for immediate close).
- **HTTP Request**: A stateless HTTP request that receives counter value and completes immediately.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can verify load balancing by observing sequential counter progression across multiple backend instances
- **SC-002**: System handles at least 100 concurrent connections without errors or duplicate counter values
- **SC-003**: Both HTTP and TCP endpoints respond within 100 milliseconds under normal load
- **SC-004**: Service runs continuously for demonstration period (hours) without crashes or connection refusals
- **SC-005**: Developer can deploy and start the service with a single command

## Assumptions

- Counter reset on server restart is acceptable - no persistence required
- Simple plain-text response format is sufficient for both protocols
- Standard TCP/HTTP connection limits apply (no custom tuning needed)
- Target environment: Linux/macOS for development, containerizable for deployment
- Sample clients will be provided to demonstrate HTTP requests and all TCP command types (numeric, "OPEN", arbitrary)
- Load balancer configuration is external to this service (service only provides counting endpoints)
- Authentication/authorization not required - demonstration/testing tool only
- IPv4 is sufficient - IPv6 support not required
- Counter overflow handling not critical for demonstration use case (restart before overflow)
