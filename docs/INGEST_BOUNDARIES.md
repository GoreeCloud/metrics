# Ingest admission and resource limits

The Metrics hub applies an early header/credential and request-size admission gate to POST /api/v1/ingest before FastAPI parses untrusted JSON. This is separate from and does not replace node-specific authorization inside the route. All other API operations keep their existing permissions.

- Require exactly one X-Agent-Token field that matches some currently configured agent. Unknown credentials are denied 401 before body parsing, without exposing which node owns a credential. A valid token for a different node is still denied later by node-specific authorization.
- Require Content-Type application/json. Missing or unrelated content type is denied 415.
- Reject a nonnumeric/duplicated Content-Length; reject bodies over 65,536 bytes by Content-Length or bounded streaming with HTTP 413. Chunked/no-length requests are also bounded while arriving.
- No extra inbound network listener or new persisted credentials are created. Early errors retain no-store and other API security headers. One bounded request is not a substitute for a trusted reverse proxy, connection/aggregate rate limits, concurrent connection caps, or deliberate DOS resilience testing.

**Status:** source implemented with synthetic positive/negative tests. Production ingress, host load, slow-client admission and end-to-end TLS policy acceptance remain open.
