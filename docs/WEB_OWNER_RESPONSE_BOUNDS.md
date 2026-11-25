# Browser owner API response limits

All React dashboard JSON GET requests now pass through one audited owner transport. It denies redirects, omits cookies and referrers, requests JSON only, preserves the administrator credential only in the Authorization header, and enforces a **12-second entire-request deadline** with an AbortController.

Before parsing, the transport checks a reported Content-Length and also counts actual response-body chunks so a server or proxy that omits or lies about Content-Length cannot grow browser memory without bounds. The response is capped at **4 MiB**; invalid content types, invalid UTF-8, malformed JSON, missing response bodies, authentication failures, and unexpected redirects fail closed. The raw response contents and token are never inserted into error messages.

The existing CSV export remains a separately bounded owner-initiated streaming operation; the native Flutter JSON helper already has an independent 4 MiB limit and redirect refusal. Tests exercise the **real TypeScript helper** using synthetic Fetch responses, including streaming overflows, unsupported media types and token-safe failures. This is a source/CI defense, not a substitute for TLS, reverse-proxy request controls, server-side admission limits, browser QA or GoreeShield data-policy acceptance.
