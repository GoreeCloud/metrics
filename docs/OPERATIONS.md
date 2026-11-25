# GoreeCloud Metrics — Development Operations

## Credentials

Generate unique administrator and per-agent token strings locally using:

~~~sh
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
~~~

Store generated values in an owner-only environment file or approved secret manager. For local hub development:

~~~sh
export METRICS_ADMIN_TOKEN='ADMIN_SECRET_INSERTED_LOCALLY'
export METRICS_AGENT_TOKENS='{"host-a":"DISTINCT_AGENT_SECRET_INSERTED_LOCALLY"}'
export METRICS_DB_PATH="$PWD/data/metrics.sqlite3"
python -m uvicorn server.app:app --host 127.0.0.1 --port 8093
~~~

For a locally running agent:

~~~sh
export METRICS_NODE_ID=host-a
export METRICS_AGENT_TOKEN='DISTINCT_AGENT_SECRET_INSERTED_LOCALLY'
export METRICS_HUB_URL=http://127.0.0.1:8093
python -m agent.agent --once
~~~

The agent token must match its node ID in the server mapping. Never paste actual tokens into GitHub or logs. Use trusted HTTPS reverse proxy and a private network for remote hosts; the agent rejects non-loopback HTTP by design.

## Native and web clients

The Vite development server proxies /api to local port 8093. Production assets must be served under the same verified HTTPS origin as /api; CORS is disabled by default. On Linux, run the Flutter Linux desktop runner. On Android, the device must reach a trusted HTTPS endpoint.

## Service deployment

The systemd agent unit template runs under a dedicated non-root metrics account and reads owner-protected environment variables from /etc/goreecloud-metrics/agent.env. Verify its install paths, permissions and runtime before enabling. It is not automatically installed.

Optional Docker Compose has a localhost-only hub port, read-only root filesystem, nonroot image user, all Linux capabilities dropped and a managed data volume. GoreeCloud Containers remains the preferred platform once independently validated for the intended host. Do not start the new service on a migration-frozen legacy VPS.

## Checks

~~~sh
python -m pytest -q
python -m compileall -q agent server
cd web && npm ci --ignore-scripts && npm run build
cd ../apps/native && flutter pub get && flutter analyze && flutter test
~~~

If a CI job or build fails, investigate before any release. Confirm production database storage and restore point before upgrades.

## Recovery and retention

A dedicated [safe storage operations guide](STORAGE_RECOVERY.md) covers integrity checks, SQLite online backup and isolated restore rehearsals. No automatic backups or production restore have been performed.


A consistent SQLite backup requires using SQLite's online backup API or stopping the service and taking a snapshot of the database with its WAL/SHM. Restore onto a separate authorized test path and validate the schema and sample queries before trusting a backup. No automated backups, schema migrations or restored deployment have been tested by this preview. The 30-day data purge occurs on ingestion only; configure an approved privacy-aware scheduled purge if needed later.

## Alerts and notifications

See [alert rules and opt-in worker](ALERTS.md). The notifier is an operator-managed process and is disabled unless started. The sample \`deploy/systemd/metrics-notifier.service\` requires an authorized non-root metrics account, an existing owner-controlled hub environment file and matching writable SQLite storage. Enabling outbound webhook delivery is an additional explicit security/privacy decision; it is not a verified GoreeCloud Notify integration.

## Notification worker delivery claims

Event delivery is a bounded best-effort operation. The SQLite alert worker atomically reserves each event immediately before its HTTPS request with a 60-second claim, limiting duplicate delivery from concurrent worker instances; expired claims can be retried after a crash. Multiple workers are not needed for development, and leases do not guarantee exactly-once delivery. Keep webhook destinations consent-approved and use idempotency at the receiver where available.

For optional one-shot notifications, a nonzero exit now indicates failure to send at least one attempted event. See [worker lease and one-shot safety](ALERT_WORKER_SAFETY.md); no runtime alert sender is installed by these tests.

## Isolated real HTTP acceptance

Run the [loopback source integration fixture](LOCAL_STACK_ACCEPTANCE.md) on a trusted developer machine to exercise actual Uvicorn, agent HTTP, SQLite and authenticated reads against disposable synthetic telemetry. This does not prove production TLS, container-engine permissions, device acceptance or release readiness.

## Raw telemetry portability

See [owner-only bounded CSV export](DATA_PORTABILITY.md) for raw host history, stable-page cursor headers, numeric-cell protection and sharing limitations. This export is not a backup or a transactional all-systems snapshot.
