# Metrics storage recovery and retention operations

**Development-stage utility:** `python -m server.storage_cli` runs as an explicit operator command; it never starts a background service or performs a production restore.

Use an authorized nonproduction database to rehearse:

~~~sh
python -m server.storage_cli --database ./data/metrics.sqlite3 verify
python -m server.storage_cli --database ./data/metrics.sqlite3 backup ./metrics-backup.sqlite3
python -m server.storage_cli restore-rehearsal ./metrics-backup.sqlite3 ./metrics-rehearsal.sqlite3
python -m server.storage_cli --database ./metrics-rehearsal.sqlite3 retention --days 30
# Only after inspecting the preview:
python -m server.storage_cli --database ./metrics-rehearsal.sqlite3 retention --days 30 --apply
~~~

Backup uses SQLite's online backup API and does not overwrite destinations. The tool validates the database schema and SQLite quick_check, creates owner-only (0600) snapshots and reports SHA-256 checksums for recorded recovery evidence. Restore rehearsals create a **new database**, never replace an existing file. The retention command is dry-run unless `--apply` is specified.

**Limitations:** this does not schedule backups, encrypt off-host copies, establish disaster recovery, restore a running production database, rotate secrets, or validate application upgrades. Retention defaults to 30 days in the hub; the standalone CLI supports explicitly chosen 1–365 day cleanup periods and requires separate execution. Protect copied files and remove only after applicable preservation requirements.
