# GoreeCloud Metrics — per-node key rotation

The hub accepts the previous single-string JSON mapping in METRICS_AGENT_TOKENS unchanged. For an explicitly controlled key rotation window, one node can temporarily use **up to two** distinct bearer tokens via a JSON array:

~~~json
{"node-a":["EXISTING_TOKEN_FROM_SECRET_MANAGER","NEW_DISTINCT_TOKEN_FROM_SECRET_MANAGER"],"node-b":"ITS_OWN_TOKEN"}
~~~

Both node-a tokens identify node-a only. Neither authorizes another node, admin endpoints, or the optional Mesh status-only scope. All agent keys must be unique across every registered node, distinct from the admin and status tokens, safe ASCII, and 32–1024 characters. Reuse, weak keys or more than two keys per node fail startup.

**Operator-controlled rotation sequence:** make a reviewed SQLite backup; generate a new strong key privately in the approved secrets manager; update the hub's environment to the two-token overlap and restart it through the approved deployment mechanism; verify health and authenticated test telemetry; update the one authorized node agent to use the new key, verify a fresh sample; then remove the previous key from the hub configuration and restart. Verify the retired key is rejected and document key custody and rollback without ever logging or printing the secret. Restart is required; editing an environment file alone does not change a running process.

**Limitations:** there is no remote user/admin key rotation UI or automatic secret rotation, tenant binding, identity provider integration, or production adoption. Never include real tokens in Git history, CI outputs, Drive docs or shell history.
