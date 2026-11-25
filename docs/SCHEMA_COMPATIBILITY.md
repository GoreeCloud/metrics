# SQLite schema-version compatibility

The Metrics hub records its owner-local SQLite schema revision using SQLite's built-in PRAGMA user_version. The present source layout is **version 1**: registered hosts, historical host samples and optional container samples. This is an incremental migration foundation, **not** a production database migrator or new encryption format.

On initialization, a fresh database receives schema version 1. A previous unversioned database (user_version 0) with the original valid host and sample layout is accepted and retains its data; missing container tables/indexes are added if necessary and the database version is marked 1. An unsupported/future schema version, missing core tables, or incompatible preexisting table columns **fails startup instead of silently replacing data**.

**Operator safeguards:** Before any software upgrade, make a consistent owner-only SQLite backup, perform a separate restore rehearsal, test the upgrade on that copy and verify host/container rows and the user_version value. A crash between idempotent CREATE TABLE and version marking can be retried; do not assume that a partially upgraded or corrupted file is repaired without independent integrity checks. Do not downgrade an app against a newer database. The normal server API does not offer remotely-triggered schema modifications.

## Read-only inspection

~~~sh
python -m server.storage_cli --database /path/to/authorized-copy.sqlite3 verify
# On an authorized offline copy only, use a SQLite client to inspect PRAGMA user_version.
~~~

**Verified:** synthetic fresh-database, legacy preservation, future-version denial and incomplete-schema denial unit tests. **Outstanding:** future versioned migration framework, production upgrade/rollback rehearsals, concurrent writer/backup acceptance and disaster recovery sign-off. No production SQLite file was modified.

**Existing-file identity checks:** Hub initialization now refuses a database that contains unrelated tables without the complete host/sample core, a container-only orphan layout, or an already-versioned v1 database with missing core/container tables. The check occurs before switching SQLite to WAL mode; opening an incompatible database for inspection does not intentionally convert its journaling mode. An empty new database and complete legacy unversioned core remain supported. Recovery requires a verified owner backup, not an automatic destructive rebuild.

The runtime database path itself must not be a symbolic link, including a broken symlink; the hub refuses this configuration rather than following a redirect to an unrelated file. This aligns with the read-only storage CLI's existing path safeguard. Directory permissions and authenticated local ownership remain the operator's responsibility.
