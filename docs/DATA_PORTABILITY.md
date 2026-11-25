# Owner-controlled host telemetry export

For data portability and authorized recovery review, the Metrics hub provides an **administrator-only** CSV export of raw host sample history:

```text
GET /api/v1/systems/{node_id}/export.csv?hours=24&limit=1000
Authorization: Bearer [owner-admin-token]
```

The `hours` window is 1–8760 (up to 365 days); `limit` is 1–10000 rows per request. Results are newest first and contain only the selected host ID, sample ID, Unix UTC timestamp, CPU/memory/disk percent, memory/disk bytes, cumulative network RX/TX bytes and uptime. **No credentials are included in the output.** Responses have `Cache-Control: no-store` and a safe attachment filename derived from a validated node ID.

For a complete large export, capture the response header `X-Export-Until-Ts` once, then pass that same value as `until_ts` on every subsequent request. If `X-Next-Before-Id` is present, supply it as `before_id` for the next page; stop when that header is absent. The stable end-time and descending sample-ID cursor avoid duplicate rows from concurrent new ingests. The client must protect the CSV as host-private telemetry, respect the intended retention and sharing policy, and verify total rows before relying on an archive. A separately authorized deletion or retention policy may remove rows between requests; CSV download is not a transactional full-database snapshot.

All numeric cells are explicitly converted to numbers rather than emitting arbitrary SQLite text into spreadsheet formulas; tampered invalid records fail the export. The node ID is constrained to a safe identifier. This endpoint is intentionally separate from the bounded chart aggregation endpoint; changing display resolution does not modify raw samples.

**Tests:** two-node synthetic private SQLite database, cursor-paged export and exact one-host isolation, unauthorized read denial, invalid bounds, safe filename/headers, and a deliberately formula-like corrupted record that must never appear in the downloadable result. No live database was accessed. This does not establish production data-subject request identity, encrypted storage/export, backup expiration, or secure sharing.
