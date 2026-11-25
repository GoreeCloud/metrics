# GoreeCloud Metrics — Security and Privacy

**Development-stage threat model:** unauthorized disclosure of hostname/resource state, forged samples, credential leakage, public HTTP exposure, resource exhaustion, local host compromise, damaged SQLite data, and unsafe future container socket access.

## Implemented safeguards

- Hub startup requires strong unique agent tokens and an independent 32+ character administrator bearer token. Registered nodes are an explicit allowlist. Non-health API endpoints require authentication.
- Agent refuses cleartext remote HTTP and relies on OS certificate validation. Local instructions bind the hub to loopback; the optional Compose example also maps only loopback.
- Pydantic bounds samples and system names. SQLite queries are parameterized; host/container history is pruned during ingestion using a validated 1–365-day retention setting (default 30 days).
- Application credentials remain in process memory, not persisted in web browser storage or Flutter app storage. Agent error logs omit HTTP URLs and bodies.
- Host agent has no remote shell, no inbound listener, and no cloud telemetry. Optional Podman/Docker stats are disabled unless explicitly configured; Docker socket access must be separately authorized and can carry root-level risk.

## Not yet secure for unrestricted deployment

- No users/roles/OIDC/MFA, built-in TLS termination, multi-factor session security, configurable audit log, secret rotation API, at-rest token hashing, brute-force controls, IP-level throttling, or production DDoS protections.
- Simplified fixed 5-second per-node throttling does not prevent all resource-exhaustion attacks; place behind trusted rate-limited ingress.
- Default threshold endpoint returns current-state indicators only. An optional separate worker can journal transitions and send HTTPS webhook notifications *only* to an explicitly configured endpoint; apply GoreeShield consent and destination reviews first. GoreeCloud Notify API tokens must remain in a protected worker environment, and its optional adapter refuses cleartext HTTP.
- Purge occurs during ingest. A paused system will retain historical data until next ingest or a manual controlled purge.
- SQLite backups must be consistent (use online backup API or stop service and preserve DB/WAL/SHM). Encryption, restore tests, migration support and storage corruption handling require validation.
- Never expose the API directly to the public Internet; use least-privilege accounts, HTTPS, strict firewall rules and private network access. Never mount a Docker socket casually.

## Responsible disclosure

Report security concerns privately using the repository security reporting capability where available. Do not include secrets or production data in public issue reports. No formal security audit or device acceptance is claimed.

## Integration status isolation

An optional, distinct status-only bearer token enables an owner-held minimal GET /v1/status route. The token cannot access private system metrics, agent ingestion or alert events; an unset token disables status responses. The status projection includes only an owner schema identifier, state and UTC observation timestamp; see [status-only source contract](MESH_STATUS_CONTRACT.md). No GoreeCloud Mesh, Identity or Wardveil runtime is implied.

### Early ingest admission

A 64 KiB streamed-body gate rejects unauthenticated, oversized or wrong-content-type ingest requests before JSON/Pydantic parsing. It does not replace node-specific credential checks, edge rate limits or production transport controls; see [ingest boundaries](INGEST_BOUNDARIES.md).
### Controlled agent credential rollover

Each node may temporarily permit a maximum of two unique agent bearer tokens during an operator-managed key rotation. Previous single-secret mappings remain valid. Distinct admin and status scopes are required. Rotation requires a controlled restart; see [credential-rotation guide](AGENT_TOKEN_ROTATION.md). No identity provider or automatic key lifecycle is implemented.
### Schema version compatibility

A Metrics database with a newer or malformed core schema fails startup rather than silently changing records; the documented version 1 baseline preserves compatible old host samples. A source-tested schema marker does not replace verified production migrations or backup/rollback acceptance.

### Agent destination and one-shot result

Agent ingestion refuses HTTP redirects so credentials are not forwarded to a newly selected origin, and --once exits nonzero when the hub does not accept the sample. Outbound logs avoid raw URLs, tokens and response content; see [agent delivery safety](AGENT_DELIVERY_SAFETY.md). TLS acceptance and production network tests remain outstanding.

### Explicit browser origins

The optional METRICS_ALLOWED_ORIGINS configuration requires up to 32 exact HTTPS origins (HTTP only for loopback) and refuses wildcard, credentials and malformed URLs at startup. CORS is independent of API bearer authentication; see [origin policy](CORS_POLICY.md). Production proxy and browser acceptance remain open.
