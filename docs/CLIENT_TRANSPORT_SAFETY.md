# Administrator-client request boundaries

The web dashboard and Flutter Linux/Android native clients contact only the configured Metrics hub. Hub URLs must be trusted HTTPS except explicit loopback development, and administrator credentials remain in client memory rather than durable storage.

For authenticated API reads the web dashboard now sets Fetch redirect mode **error**, refusing redirects rather than allowing the user-agent to follow them. The native Flutter client issues explicit GET requests with followRedirects disabled and refuses 3xx responses. The Flutter implementation additionally limits JSON response body accumulation to 4 MiB, with a bounded per-response stream timeout. This is a defensive limit, not a replacement for strict authenticated server pagination.

Native synthetic client tests confirm that redirected requests are not followed, authorization remains attached only to the source request, oversized JSON is rejected, and non-success responses are not treated as data. A web source regression test verifies the redirect policy. These tests do not connect to an external domain.

**Outstanding:** real supported-browser and OS TLS/certificate verification, proxy and native device QA, redirect behavior from actual adversarial remote servers, service identity pinning policy, accessible failure messaging, authenticated session lifecycle and release acceptance. No live credentials or production endpoints are involved in these tests.
