# Bounded time-series chart history

The admin-only `GET /api/v1/systems/{node_id}/history` endpoint supports an explicit time window `hours=1..168` (24-hour default) and a display resolution `points=24..1000` (400 default). It groups **all** samples in the requested interval into evenly sized SQLite time buckets instead of discarding older records after a 5,000-row tail limit. The response remains chronological and carries a `bucket_seconds` value and `sample_count` for each bucket.

CPU, memory and disk utilization are averages for each bucket. Memory/disk byte values use integer averages; cumulative RX/TX and uptime fields use the maximum observed value within a bucket. These are **display summaries**, not raw individual samples or guaranteed packet accounting. The client can choose fewer buckets for slower devices; aggregated curves can obscure short-duration spikes, so alert state continues to use the latest full-resolution host snapshot, not aggregated history.

The query is owner-admin authenticated, validates node IDs and query bounds, excludes future timestamps, and uses the existing node/time SQLite index. Its Python output never materializes more than 1,000 chart rows per request, even for the full 7-day window. The underlying SQL still scans applicable historical rows and must be evaluated against realistic multi-host datasets before production scale claims.

**Tests:** synthetic host with 8,000 samples spanning more than 22 hours verifies that data beyond the former 5,000-row tail contributes to the oldest and newest buckets. The test also checks bucket cardinality, sample counts, chronological ordering, invalid query bounds, unknown-node refusal and authorization. No production telemetry was accessed.
