# GoreeCloud Metrics — Roadmap

**Phase 1: Source-backed preview.** Hub, host agent, web interface, native Linux/Android runners, tests, CI, documentation and local setup. Validate toolchains and run reliable smoke tests; do not declare production readiness.

**Phase 2: Storage and operational reliability.** Schema migrations, backups/restores, performance, resilience, improved throttling, configurable retention, agent token rotation and operational alerts.

**Phase 3: Observability breadth.** Optional Docker/Podman container statistics after socket security review, disks/GPU/temperature opt-in metrics, threshold management, alert delivery and flexible charts.

**Phase 4: Ecosystem integration and acceptance.** Confirm GoreeCloud UI visual compliance, approved Identity and GoreeCloud Mesh API contracts, GoreeShield retention controls, Wardveil security boundaries, Linux packaging, Android signing/device tests, controlled rollouts and evidence for release classification.

These phases have no invented completion dates.

**Schema checkpoint (development):** SQLite version 1 baseline and in-place unversioned compatible host/containers table adoption are source-tested. Future versioned data migrations, operator-reviewed backup/recovery and production lifecycle acceptance remain open; see [schema compatibility](SCHEMA_COMPATIBILITY.md).

**History checkpoint:** the authenticated history endpoint now aggregates the full 1–168 hour interval to a bounded number of chart buckets; see [history aggregation](HISTORY_AGGREGATION.md). Multi-host sustained-load and presentation-scale validation remain outstanding.

**November 25, 2026 source checkpoint:** Per-host indexed latest-sample lookup, database identity/symlink safeguards, bounded administrator web/native JSON transport, and explicit cancellable browser CSV download have passed protected branch CI and merged. This records implemented source only; real host load, recovery on owner databases, browser and device accessibility, secure release signing, and production MIPS/operations acceptance are still outstanding.
