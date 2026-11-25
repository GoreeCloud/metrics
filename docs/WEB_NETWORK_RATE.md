# Web network-throughput cards

The React overview displays the host's total received and transmitted byte counters separately from the last measured network transfer *rate*. When an owner selects a host, the client makes an administrator-authenticated GET of the counter-safe `/api/v1/systems/{node_id}/network-rate` endpoint with no-store caching and redirects rejected; polling follows the existing bounded 15-second snapshot refresh.

Rates are expressed as bytes per second using the same formatting rules as other host byte values. When there are fewer than two samples, an invalid/stale interval, or a host restart / counter reset, the UI displays an em dash and an explanatory state—not a fabricated zero. In-flight responses for an older selected host are ignored. The token remains in React memory; the application does not save credentials or history in browser storage.

These cards use the existing canonical GoreeCloud UI CSS semantic tokens and responsive layout. Tests validate code contracts, TypeScript compilation, and the web production build. Real network hosts, live browser assistive technology, and approved physical-device acceptance have not been tested. The feature depends on the authenticated counter-rate backend.
