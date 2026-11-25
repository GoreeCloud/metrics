# Opt-in container statistics

**Disabled by default.** The host agent can collect a *read-only snapshot* from a locally installed container CLI when the operator sets `METRICS_CONTAINER_PROVIDER=podman` or `METRICS_CONTAINER_PROVIDER=docker`. It never starts, stops, enters or modifies containers.

Podman rootless is preferred for least privilege. Do **not** add an ordinary agent account to the Docker group automatically: daemon-socket access often provides host-root-equivalent capabilities. Docker collection is an explicit, high-risk opt-in requiring a host-specific threat review. Do not mount the Docker socket into the GoreeCloud Metrics hub or service containers.

Supported payload: up to 100 container names, each with bounded CPU%, memory%, and network-byte counters. Stats calls use an argument-list subprocess with a six-second timeout, a 200KB output cap, and no shell. CPU values are clamped to 0–100; they may not accurately represent multi-core utilization above 100% from upstream engines. Container identifiers may change across recreation. This feature is intentionally limited and needs representative Podman and Docker runtime verification.

The hub persists per-container samples with the host sample in SQLite and exposes an authenticated current container snapshot endpoint. No cross-host orchestration access, controls, mounts, sensitive environment variables, or container logs are collected.

The local container provider subprocess now streams stdout into a 200,000-byte fixed ceiling with a six-second total deadline. Oversized, failed or unresponsive provider processes are terminated, and normal host telemetry remains available. See [output boundary](CONTAINER_OUTPUT_SAFETY.md). This does not authorize privileged Docker-socket access.
