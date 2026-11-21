# GoreeCloud Metrics owner-held status contract (development only)

Metrics owns its data and API. GoreeCloud Mesh owns ecosystem integration and must not implicitly receive a Metrics administrator or per-host ingestion token. The independent development-phase source contract is a narrow **GET /v1/status** route, disabled unless an operator explicitly provides a unique **METRICS_STATUS_TOKEN** (32–1024 safe ASCII characters). This is informed by the independently verified status-only development pattern in GoreeCloud Wardveil and its Mesh synthetic owner contracts; the service name and schema version are Metrics-owned, not a negotiated stable Mesh interface.

The status token cannot query private host/asset details, historical samples, Prometheus metrics, alert events or agent ingestion; those routes retain independent permissions. An unset status token makes /v1/status return 404 even to a valid administrator. A wrong token returns 401. The endpoint rejects queries and bodies, does not accept arbitrary paths, and emits only:

~~~json
{"schema_version":"metrics.status.v1","state":"ok","observed_at":"2026-11-21T00:00:00.000Z"}
~~~

The example timestamp is illustrative, not current telemetry. The real response timestamp is UTC; degraded database access returns a 503 response with the same three fields and state "degraded". It does **not** disclose hostnames, node IDs, counts, measurements, credentials, filesystem paths or private security events. Headers include no-store and nosniff, and authentication is checked before probing the database.

This contract is not an active Mesh connection, a production deployment, Identity actor authorization, or a license to share family telemetry. Future Mesh integration requires an explicit GoreeShield-approved purpose, fixed trusted transport (with real TLS/service identity for remote use), Mesh owner and Identity permissions, a managed status-token lifecycle, negative scope tests, cancellation, outage handling, and a source-owner versioned contract review. Wardveil security owns threat detection; this endpoint is observability status only.

No network request is initiated by the status endpoint. Source and synthetic authentication tests run as part of the Metrics API test suite.
