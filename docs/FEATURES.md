# GoreeCloud Metrics — Feature Status

| Feature | Implementation source | Outstanding acceptance |
| --- | --- | --- |
| Authenticated host ingestion | Implemented | API runtime and load tests |
| CPU, memory, disk, network totals, uptime | Implemented via psutil | Real host validation |
| Configurable SQLite 1–365-day ingest-time retention (30-day default) | Implemented and tested | Long-running operation and scheduled purge verification |
| Configurable online/utilization alert thresholds | Implemented | Timing and false-positive evaluation |
| Persistent alert transition journal and opt-in HTTPS worker | Implemented with synthetic tests | End-to-end authorized delivery and service acceptance |
| Authenticated Prometheus text format | Implemented | Downstream integration |
| React systems, trends and current alerts | Implemented | Browser and accessibility tests |
| React container snapshots and alert-transition history panels | Implemented in client source; backend API merge required | End-to-end UI/API integration testing |
| Flutter Linux client | Implemented; CI bundle artifact configured | Build verification, desktop runtime, installer |
| Native container snapshot / alert-transition views | Implemented in Flutter source | API integration and physical-device acceptance |
| Flutter Android client | Implemented; CI debug APK artifact configured | Verify artifact, signing and physical-device test |
| Docker and Podman read-only container snapshots | Implemented, disabled by default | Real running-container validation and explicit Docker permission review |
| Persistent alert transition journal and opt-in HTTPS worker | Implemented with synthetic tests | Authorized real delivery and service acceptance |
| GoreeCloud Notify topic-publish adapter | Implemented and synthetically tested | Real HTTPS service auth, delivery and privacy acceptance |
| In-app alert editor / mobile push delivery | Not implemented | Privacy and delivery review |
| Centralized Identity, Mesh and Wardveil APIs | Not implemented | Verified service contracts |
| SQLite backup and isolated restore-rehearsal CLI | Implemented with tests | Independent production recovery acceptance |
| Production deployment and restore rehearsal | Not implemented | Operations acceptance |
| Native Flutter GoreeCloud UI Lagoon semantic tokens | Implemented from verified immutable alpha snapshot | Founder visual review, device accessibility and full native component acceptance |
| Optional status-only bearer scope for future Mesh use | Source implemented; fail-closed tests | Real Mesh admission, Identity, policy and transport acceptance |
| SQLite schema version 1 and fail-closed legacy compatibility | Fresh/legacy/future synthetic migration tests | Approved future migration framework, production rehearsals and rollback |
