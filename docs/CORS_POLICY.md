# Browser cross-origin admission

`METRICS_ALLOWED_ORIGINS` is optional and disabled by default. When configured, the Metrics hub now requires a comma-separated list of **at most 32 exact origins**. Remote origins must use HTTPS; HTTP is accepted only for `localhost`, `127.0.0.1`, or the IPv6 loopback address `[::1]`. An origin is just scheme, host and optional explicit port—no path, trailing slash, query, fragment, username, password, wildcard, embedded spaces or invalid port. Malformed configuration **fails at startup** instead of silently broadening browser access. Repeated identical origins are deduplicated.

A safe development example is `METRICS_ALLOWED_ORIGINS=http://localhost:5173`. A remote deployment may use a reviewed exact HTTPS origin such as `https://metrics.example.test`, but must verify its actual DNS, TLS and authorization independently. The normal same-origin deployment does not need this setting.

The server only exposes GET to configured CORS origins, and authorizes private data with a separate administrator bearer credential. **CORS is not authentication or network firewall policy.** A browser outside the allowlist must not receive the `Access-Control-Allow-Origin` response header, but nonbrowser clients can still issue HTTP requests; they remain subject to API credentials, transport security and network controls. No live browser deployment or remote origin was configured by this source change.

Synthetic parser tests reject malformed, wildcard and remote cleartext values; a local ASGI response test verifies that only a specifically allowed Origin receives the CORS header. Production reverse-proxy, TLS and GoreeCloud Identity acceptance are still outstanding.
