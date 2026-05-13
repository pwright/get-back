<!--
Sync Impact Report:
Version: 0.0.0 → 1.0.0 (Initial constitution)
Added sections:
  - Core Principles (4 principles focused on simplicity and dual-protocol design)
  - Architecture Constraints
  - Development Workflow
Templates requiring updates: N/A (initial creation)
Follow-up TODOs: None
-->

# Get-Back Constitution

## Core Principles

### I. Simplicity First
The implementation MUST prioritize simplicity over cleverness or premature optimization.
- Straightforward logic over abstractions
- Minimal dependencies - standard library preferred
- No frameworks unless absolutely necessary
- Code should be readable and maintainable by developers unfamiliar with the project

**Rationale**: Simple code is easier to debug, maintain, and reason about. Complexity should only be introduced when solving actual problems, not anticipated ones.

### II. Dual Protocol Support
The application MUST expose two distinct network interfaces:
- TCP port: raw TCP connections for binary or text protocols
- HTTP port: RESTful HTTP endpoints for web clients
- Both protocols MUST be functional, tested, and documented
- Protocol handlers MUST share core business logic without duplication

**Rationale**: Different clients have different needs. TCP provides low-level control, HTTP provides web compatibility. Supporting both from the start ensures the architecture remains protocol-agnostic.

### III. Clear Boundaries
Components MUST have well-defined responsibilities and interfaces:
- Protocol handlers (TCP/HTTP) handle only protocol concerns
- Business logic is protocol-independent
- No mixing of transport, application, and data layers
- Each component can be tested in isolation

**Rationale**: Clear separation enables testing individual components, swapping implementations, and understanding the system without reading all the code.

### IV. Observable Behavior
The system MUST be easy to debug and monitor:
- Structured logging at appropriate levels (info, warn, error)
- Connection lifecycle events logged (accept, close, error)
- Request/response patterns traceable
- Health/status endpoints available

**Rationale**: When things go wrong in production, logs and observability are the first line of defense. Build it in from the start.

## Architecture Constraints

### Technology Selection
- Language choice deferred to planning phase (Python or Go both acceptable)
- Standard library networking primitives preferred over frameworks
- Dependencies MUST be justified (document why standard library insufficient)
- No ORMs, heavy frameworks, or "magic" libraries without explicit approval

### Port Configuration
- TCP and HTTP ports MUST be configurable via environment variables or command-line flags
- Sensible defaults provided (e.g., TCP: 8001, HTTP: 8000)
- Both servers MUST be able to run concurrently in the same process
- Graceful shutdown MUST close both ports cleanly

### Error Handling
- Network errors MUST NOT crash the server
- Per-connection errors MUST be isolated
- All errors MUST be logged with sufficient context
- Client errors vs server errors clearly distinguished

## Development Workflow

### Testing Requirements
- Unit tests for business logic (protocol-independent)
- Integration tests for each protocol handler
- End-to-end tests exercising both TCP and HTTP paths
- Tests MUST pass before merging
- No mocking of standard library networking (use real sockets in tests)

### Documentation Standards
- README MUST explain how to run the server
- Protocol specifications MUST be documented (TCP message format, HTTP endpoints)
- Configuration options MUST be listed
- Example client code for both protocols provided

### Code Review Focus
- Is it simple? Could it be simpler?
- Are boundaries clear?
- Is it testable?
- Is error handling appropriate?

## Governance

This constitution guides all architectural and implementation decisions. When in doubt, favor simplicity and clarity over performance or features.

Amendments to this constitution require:
1. Clear rationale for the change
2. Impact assessment on existing design
3. Updated documentation

Complexity MUST be justified. Features MUST solve real problems. Abstractions MUST earn their keep.

**Version**: 1.0.0 | **Ratified**: 2026-05-13 | **Last Amended**: 2026-05-13
