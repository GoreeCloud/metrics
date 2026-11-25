# Metrics — explicit privacy deletion and complete history retention

The operator-only SQLite utility includes a deliberately separate, **dry-run by default**, per-node erasure operation. The command targets only a deliberately selected node ID, after verifying it is registered in the selected Metrics database. It previews the number of system, host sample, container sample, alert-state and alert-event rows; an operator must add --apply for an atomic deletion:

~~~sh
python -m server.storage_cli --database /path/to/authorized-copy.sqlite3 forget-node --node-id node-a
# Only after reviewed preview, backup and an explicit authorization:
python -m server.storage_cli --database /path/to/authorized-copy.sqlite3 forget-node --node-id node-a --apply
~~~

**Caution:** --apply permanently removes the node and its associated rows from the *selected* SQLite database, including alert history. The command does not invalidate its enrollment token in METRICS_AGENT_TOKENS; an active agent with that still-valid key can re-register on next successful ingest. Revoke the key separately and stop the source agent, then verify both policies. SQLite WAL, snapshots, copied backups, logs and other authorized downstream recipients can retain previous data; manage those through separate approved retention and recovery processes. A SQL DELETE does not certify forensic secure erasure.

The existing retention CLI now previews/cleans both host and container samples, not only host samples. The command still defaults to read-only preview and only deletes with --apply and an explicitly validated 1–365 day threshold. It does not purge alert events (those follow the separate notifier journal policy) or stale host registry rows. A running hub can ingest between preview and apply, so use controlled maintenance and separate backups. No command in this guide has been executed on a production database.

**Status:** tested with an isolated synthetic Metrics API SQLite database, including two registered nodes and alert journal preservation for the unaffected node. Full GoreeShield data-subject request workflows, cryptographic backup erasure, multi-device sync and policy acceptance are not yet implemented.
