# Implementation Plan: Dual-Protocol Counter Service

**Branch**: `001-dual-counter` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-dual-counter/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a dual-protocol network service that exposes independent counters via HTTP (port 9091) and TCP (port 9092) for load balancer testing. HTTP provides simple GET-based counter access. TCP implements a command-based protocol where clients control connection lifetime (numeric = timed, "OPEN" = persistent, other = immediate close). Each protocol maintains its own atomic counter starting at 1. All counter responses include server identity (hostname/pod) to enable load distribution observation. Counters increment independently to demonstrate protocol-specific load distribution.

Web testing console (port 9093) provides interactive testing interface with request buttons, real-time counter visualization, request/response history tracking, and JSON stats API. Console acts as both observer (displays counters) and actor (makes test requests to 9091/9092), eliminating need for separate client tools during demos.

Python with asyncio provides simplicity, rapid iteration, and natural concurrent server implementation.

## Technical Context

**Language/Version**: Python 3.11+ (chosen for rapid iteration, excellent debugging, and asyncio for concurrent servers)

**Primary Dependencies**: Standard library only (asyncio for concurrent TCP/HTTP servers, logging for observability). No external frameworks required per constitution simplicity principle.

**Storage**: N/A (counters in-memory, reset on restart)

**Testing**: pytest for unit/integration tests, standard library unittest for simple cases if preferred

**Target Platform**: Linux/macOS development, containerizable (Docker) for deployment

**Project Type**: Network service / demonstration tool

**Performance Goals**: Handle 100+ concurrent connections without errors, <100ms response time under normal load (per spec SC-002, SC-003)

**Constraints**: 
- Both servers must run concurrently in single process
- Atomic counter increments (no race conditions)
- Simple implementation (standard library preferred per constitution)
- Ports configurable via environment variables or CLI flags

**Scale/Scope**: 
- Small codebase (<500 LOC estimated)
- Demonstration/testing tool (not production service)
- Two protocol handlers + shared counter logic + sample clients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First ✅

- **Standard library only**: asyncio (built-in), no external frameworks required
- **Straightforward logic**: Counter increment, protocol parsing, concurrent servers
- **Minimal dependencies**: Zero external dependencies needed
- **Readable**: Python syntax naturally readable, well-suited for unfamiliar developers

**Status**: PASS - Design prioritizes simplicity throughout

### II. Dual Protocol Support ✅

- **TCP and HTTP both implemented**: Core requirement, naturally separated
- **Both functional and tested**: Test plan covers both protocols independently
- **Shared business logic**: Counter increment logic protocol-independent (separate counter instances, same increment pattern)

**Status**: PASS - Dual protocol is the primary requirement

### III. Clear Boundaries ✅

- **Protocol handlers separate**: HTTP handler module, TCP handler module
- **Business logic independent**: Counter class/logic used by both protocols
- **No layer mixing**: asyncio server → protocol handler → counter logic
- **Isolated testing**: Each component testable independently

**Status**: PASS - Architecture naturally enforces boundaries

### IV. Observable Behavior ✅

- **Structured logging**: Python logging module (standard library)
- **Connection lifecycle logged**: Accept, close, error events
- **Counter increments traceable**: Log each increment with protocol tag
- **Health endpoints**: HTTP can provide status endpoint easily

**Status**: PASS - Observability built into requirements (FR-010)

### Overall Constitution Compliance

**Pre-Phase 0 Status**: ✅ ALL GATES PASSED

**Post-Phase 1 Status** (after design artifacts): ✅ ALL GATES PASSED

**Design Verification**:
- ✅ Standard library only confirmed in research (asyncio, logging, socket)
- ✅ Zero external dependencies (pytest only for testing)
- ✅ Clear module boundaries: counter.py, http_server.py, tcp_server.py, config.py, cli.py
- ✅ Protocol handlers separated (http_server vs tcp_server modules)
- ✅ Business logic isolated (counter.py independent of protocols)
- ✅ Comprehensive logging design (connection lifecycle, counter events)
- ✅ Observable behavior documented in contracts and data model

No complexity justification required. Design aligns perfectly with constitution principles. Implementation ready to proceed.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
getback/                    # Main package directory
├── __init__.py            # Package marker
├── __main__.py            # Entry point (python -m getback)
├── counter.py             # Counter business logic (atomic increment)
├── http_server.py         # HTTP server implementation (asyncio)
├── tcp_server.py          # TCP server implementation (asyncio)
├── console_server.py      # Web testing console (port 9093, interactive)
├── config.py              # Configuration (ports, logging setup)
└── cli.py                 # CLI argument parsing

clients/                   # Sample client implementations
├── http_client.py         # HTTP client example (requests or urllib)
├── tcp_client.py          # TCP client example (socket)
└── README.md              # Client usage documentation

tests/
├── test_counter.py        # Unit tests for counter logic
├── test_http_server.py    # Integration tests for HTTP endpoint
├── test_tcp_server.py     # Integration tests for TCP endpoint
├── test_integration.py    # End-to-end tests (both protocols)
└── conftest.py            # pytest fixtures (test servers, etc.)

Dockerfile                 # Container definition
requirements.txt           # Dependencies (pytest for testing)
requirements-dev.txt       # Development dependencies
README.md                  # Main documentation
```

**Structure Decision**: Single-package layout chosen for simplicity. All server code in `getback/` package (importable and executable via `python -m getback`). Sample clients in separate `clients/` directory to demonstrate usage. Tests mirror source structure. Flat hierarchy appropriate for <500 LOC project. No subdirectories needed - constitution simplicity principle applied.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
