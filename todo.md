# Get-Back TODO

## Refactor Duplicate Batch Client Code

**Status**: Planned, not implemented

**Issue**: `batch_http_client.py` and `batch_tcp_client.py` have ~60 lines of duplicated code:
- Latency statistics calculation (lines 58-71)
- Server distribution printing (lines 72-79)
- Error handling blocks (lines 81-103)
- Result extraction and summary (lines 46-60)

**Options**:

1. **Extract shared calculations** (Option A):
   - Create `clients/batch_stats.py` with pure functions for latency stats and distribution calculations
   - Each client imports and calls these utilities
   - Reduces each file by ~20 lines
   - Maintains independence for protocol-specific logic (argument parsing, request building, error handling)
   - **Trade-off**: Adds coupling for shared code, but enables consistent bug fixes

2. **Keep current duplication** (Option B):
   - Leave both files as-is
   - Accept 60 lines of duplicated code
   - Maintain full independence for future divergence
   - **Trade-off**: Changes to stats/formatting require manual synchronization

**Decision needed**: Choose Option A (extract) or Option B (keep separate) based on:
- Likelihood of stats calculation bugs/enhancements
- Expected rate of HTTP vs TCP feature divergence
- Preference for DRY vs standalone simplicity

**Plan document**: See `.claude/plans/i-ve-had-some-feedback-shimmering-minsky.md` for full analysis and implementation details

**User preferences**:
- HTTP and TCP clients likely to diverge significantly in future
- Prefer simple, self-contained scripts over abstraction
- Duplication acceptable if it maintains readability
