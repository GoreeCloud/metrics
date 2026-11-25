# Explicit browser raw telemetry export

The React overview provides a user-initiated CSV download for the selected host and currently selected history interval (6, 24 or 168 hours). The application uses the existing administrator-authenticated, host-scoped export API. It downloads **at most 10,000 newest raw host samples** from one API page, not the aggregated history chart. The browser shows a distinct warning if the response has an `X-Next-Before-Id` pagination cursor; completing a multi-page export requires the documented API cursor workflow and explicit additional owner action.

## Security and resource bounds

The export request uses the ephemeral in-memory administrator bearer token, `redirect: 'error'`, `cache: 'no-store'`, omits browser cookies, and suppresses referrer disclosure. It sends no credentials in URL parameters, never persists tokens, and validates the host ID and hour bounds before the request. It accepts only successful CSV responses, verifies returned pagination cursors, rejects unexpected content types, and cancels the stream if data exceeds **8 MiB**, whether or not Content-Length is provided. On download, a short-lived local Blob object URL is revoked after initiation. Exported CSV data is deliberately saved to the owner's browser-managed downloads folder; its continued storage and sharing are subject to GoreeShield privacy controls and local backup/retention policy. Data itself is not anonymized.

## Verification and limits

Node tests transpile and exercise the actual TypeScript fetch implementation with synthetic Fetch responses, including oversized streams, malformed cursors, unauthorized responses, and token-safe failures. The React app is checked with TypeScript and Vite. Browser download gestures, accessibility, multi-page extraction, raw-data format policy, and production permission acceptance remain outstanding. No real host telemetry was exported or shared during source development.
