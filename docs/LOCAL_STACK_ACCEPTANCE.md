# Isolated real HTTP stack acceptance fixture

This source-owned integration fixture launches the actual GoreeCloud Metrics FastAPI application under a temporary Uvicorn child process, binding exclusively to **127.0.0.1** on an ephemeral local port. It creates a temporary SQLite database, unique synthetic credentials, a synthetic host/container sample and no production secrets or real host metrics. The child and its database are discarded after the test.

Run in an authorized development checkout using the current tested Python dependencies:

~~~sh
python -m pytest -q tests/test_local_stack_transport.py
~~~

The test verifies readiness, a limited status-only credential, agent submission through the real Python HTTP client, SQLite persistence, administrator reads of systems/history/container samples, alert evaluation, Prometheus exposition, private nonsecret configuration, and denial of status-only access to private host records. It does not start the optional notifier worker, upload events to an outside service or execute Docker/Podman.

The fixture uses HTTP only because its actual transport is a disposable IPv4 loopback server. It must not be repurposed to waive production TLS or service identity validation. Local success does not establish a production reverse-proxy configuration, multiuser GoreeCloud Identity/Mesh admission, consent, restart/recovery behavior, Android device acceptance, release signing or operational readiness.

**Evidence:** A complete local pass against the real Uvicorn child and native SQLite tables must be verified after each related source change; it is a source-level integration smoke, not an always-on or stable deployment.
