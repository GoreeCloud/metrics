# Agent outbound delivery and safe one-shot diagnostics

The Linux host agent uses the Python standard-library HTTP transport with OS certificate verification. The outbound POST to the configured Metrics ingest endpoint rejects **every HTTP redirect**, including HTTP 302/307 to any different origin, before forwarding the per-agent credential.

For a single diagnostic invocation, run:

~~~sh
# Configure the agent's verified host ID, strong token and trusted hub URL
# in an owner-only environment or approved secrets manager first.
python -m agent.agent --once
echo $?
~~~

Exit code **0** now means the hub accepted that one sample (HTTP 202); **2** means a network failure, refused redirect, unexpected response, or another send error. The agent deliberately logs only an exception **type** on send failure—never a request URL, response body, token, or hostname. Input-configuration failures remain argparse nonzero exits.

An isolated loopback integration test starts two temporary local HTTP servers: one tries to redirect the credential-bearing ingest request, and the other records whether any request arrived. No secret is transmitted to the second server. Other tests verify successful/failed one-shot exit codes and log redaction.

**Scope:** Source-tested behavior, not proof of TLS endpoint identity, production agent rollout, full retry policy, redirect behavior in unrelated clients, or real host-device integration. Normal continuous monitoring continues with its existing periodic reporting loop.
