# GoreeCloud Metrics — Architecture

~~~text
Linux agent (psutil) -- HTTPS + agent token --> FastAPI hub -- SQLite WAL
React web       <-- HTTPS + admin token -------|
Flutter Linux   <-- HTTPS + admin token -------|
Flutter Android <-- HTTPS + admin token -------|
Prometheus      <-- HTTPS + admin token -------|
~~~

- Hub accepts only IDs provisioned in METRICS_AGENT_TOKENS. It validates bounded host statistics with Pydantic, assigns server timestamps, uses parameterized SQLite queries and prunes data older than 30 days during ingestion.
- Agent can additionally gather opt-in read-only container statistics from rootless Podman (or explicitly authorized Docker). The hub persists bounded per-host snapshots; no container lifecycle operations. Agent gathers low-privilege local statistics. It exposes no inbound port, refuses non-loopback cleartext HTTP and never executes hub commands.
- Browser React/Recharts uses memory-only token, same-origin API requests and the provisional GoreeCloud UI Lagoon token roles. Native Flutter shares UI logic across independently generated Linux and Android platform runners.
- Offline defaults to 120 seconds without a heartbeat; utilization thresholds default to 90%, and are environment-configurable. A separate single-instance operator-managed notifier journals firing/resolved transitions and can optionally forward them via an HTTPS webhook; no endpoint is configured or contacted by default.
- An optional GoreeCloud Notify topic adapter translates transitions to its verified API contract; inter-service runtime acceptance remains unverified. Future MIPS integration remains unverified. GoreeShield privacy, Wardveil security, GoreeCloud Mesh, GoreeCloud Identity, and GoreeCloud UI retain distinct responsibilities.

## Owner-held integration boundary

The optional GET /v1/status endpoint has a third independent credential, no private host fields and an explicitly minimal schema. This is a testable source-owner status seam for a future GoreeCloud Mesh connector, not a deployed integration; see [owner-held status contract](MESH_STATUS_CONTRACT.md).
