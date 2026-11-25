# Read-only Metrics storage diagnostics

The optional operator CLI reports **redacted storage readiness** for a specifically selected SQLite database. It does not require or read the hub's admin/agent tokens, start a service, contact the network, or print database paths, hostnames, node IDs, sample values, or credentials.

~~~sh
# Authorized development or separately approved operator environment:
python -m server.doctor --database ./data/metrics.sqlite3 --json
# Standard human-readable output:
python -m server.doctor --database ./data/metrics.sqlite3
~~~

The JSON fields include status, schema_version, expected_schema_version, file_permissions_owner_only, history_indexes_present, registered_hosts, host_samples, container_samples, alert_events, and the oldest/newest **host sample Unix timestamp only**. Individual host names and sample values never leave the database. The tool opens an existing regular file with SQLite mode=ro, enables query-only SQL, executes PRAGMA quick_check, validates core tables and declared index names, and never creates, repairs, or chmods a file.

Exit **0** indicates all checks passed, schema version matches the current source, expected history indexes exist and file mode has no group/other permissions. Exit **2** indicates a required check failed or the database is missing/incompatible. An invalid database reports a generic redacted diagnostic error rather than echoing local paths or exception bodies. On non-POSIX hosts, permission semantics may differ and need review.

**Limits:** A healthy SQLite file does not prove that metrics ingestion, alert delivery, TLS, disk capacity, off-host recovery, backup encryption, GoreeShield privacy policy, a native client or production runtime works. PRAGMA quick_check is a bounded diagnostic, not exhaustive full integrity verification. Counts/timestamps remain potentially sensitive operational metadata and belong in an approved private log/store; do not publish a public JSON report. A running writer may change counts between queries. No production database was inspected during implementation tests.

Tests use isolated synthetic SQLite fixtures for success, missing and foreign database files, symlinks, open permissions and future unsupported schema. It is a preview tool, not an automated health monitor.
