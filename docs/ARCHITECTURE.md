# GoreeCloud Metrics — Architecture

~~~text
Linux agent (psutil) -- HTTPS + agent token --> FastAPI hub -- SQLite WAL
React web       <-- HTTPS + admin token -------|
Flutter Linux   <-- HTTPS + admin token -------|
Flutter Android <-- HTTPS + admin token -------|
Prometheus      <-- HTTPS + admin token -------|
~~~

- Hub accepts only IDs provisioned in METRICS_AGENT_TOKENS. It validates bounded host statistics with Pydantic, assigns server timestamps, uses parameterized SQLite queries and prunes data older than 30 days during ingestion.
- Agent gathers low-privilege local statistics. It exposes no inbound port, refuses non-loopback cleartext HTTP and never executes hub commands.
- Browser React/Recharts uses memory-only token, same-origin API requests and the provisional GoreeCloud UI Lagoon token roles. Native Flutter shares UI logic across independently generated Linux and Android platform runners.
- Offline is 120 seconds without a heartbeat; utilization indicators appear at >=90%. They are not delivered notifications.
- Future MIPS integration remains unverified. GoreeShield privacy, Wardveil security, GoreeCloud Mesh, GoreeCloud Identity, and GoreeCloud UI retain distinct responsibilities.
