# GoreeCloud Metrics — Feature Status

| Feature | Implementation source | Outstanding acceptance |
| --- | --- | --- |
| Authenticated host ingestion | Implemented | API runtime and load tests |
| CPU, memory, disk, network totals, uptime | Implemented via psutil | Real host validation |
| SQLite 30-day ingest-time retention | Implemented | Restore / migration validation |
| Online and utilization indicators | Implemented | Alert behavior and timing tests |
| Authenticated Prometheus text format | Implemented | Downstream integration |
| React systems, trends and current alerts | Implemented | Browser and accessibility tests |
| Flutter Linux client | Implemented; CI bundle artifact configured | Build verification, desktop runtime, installer |
| Flutter Android client | Implemented; CI debug APK artifact configured | Verify artifact, signing and physical-device test |
| Docker and Podman statistics | Not implemented | Least-privilege opt-in design |
| Notification delivery and alert configuration | Not implemented | Privacy and delivery reviews |
| Centralized Identity, Mesh and Wardveil APIs | Not implemented | Verified service contracts |
| SQLite backup and isolated restore-rehearsal CLI | Implemented with tests | Independent production recovery acceptance |
| Production deployment and restore rehearsal | Not implemented | Operations acceptance |
