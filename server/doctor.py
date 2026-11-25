"""Read-only, redacted GoreeCloud Metrics hub storage diagnostics.

No network calls, host identifiers, credentials, paths, or sample values in output.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
from urllib.parse import quote

from server.app import SCHEMA_VERSION
from server.storage_cli import existing_database

CORE_TABLES = {"systems", "samples", "container_samples"}
HISTORY_INDEXES = {"samples_node_time", "samples_time", "container_samples_node_time"}


def check(filename: str) -> dict[str, object]:
    path = existing_database(filename)
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("Expected a regular Metrics SQLite file")
    # It is important not to chmod files from a supposedly diagnostic command.
    restricted = (stat.S_IMODE(metadata.st_mode) & 0o077) == 0
    with sqlite3.connect(
        f"file:{quote(path.as_posix(), safe='/')}?mode=ro", uri=True, timeout=5
    ) as connection:
        connection.execute("PRAGMA query_only=ON")
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result != ("ok",):
            raise ValueError("SQLite integrity check failed")
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        indexes = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )}
        missing = CORE_TABLES - tables
        if missing:
            raise ValueError("Metrics core tables missing")
        host_count = int(connection.execute("SELECT COUNT(*) FROM systems").fetchone()[0])
        sample_count = int(connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0])
        container_count = int(connection.execute(
            "SELECT COUNT(*) FROM container_samples"
        ).fetchone()[0])
        rows = connection.execute(
            "SELECT MIN(ts), MAX(ts) FROM samples"
        ).fetchone()
        alert_events = (int(connection.execute(
            "SELECT COUNT(*) FROM alert_events"
        ).fetchone()[0]) if "alert_events" in tables else 0)
    return {
        "status": ("ready" if restricted and version == SCHEMA_VERSION
                   and HISTORY_INDEXES.issubset(indexes) else "review_required"),
        "schema_version": version,
        "expected_schema_version": SCHEMA_VERSION,
        "file_permissions_owner_only": restricted,
        "history_indexes_present": HISTORY_INDEXES.issubset(indexes),
        "registered_hosts": host_count,
        "host_samples": sample_count,
        "container_samples": container_count,
        "alert_events": alert_events,
        "first_host_sample_unix_ts": rows[0],
        "last_host_sample_unix_ts": rows[1],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only, redacted GoreeCloud Metrics SQLite storage diagnosis"
    )
    parser.add_argument(
        "--database", default=os.environ.get("METRICS_DB_PATH", "./data/metrics.sqlite3")
    )
    parser.add_argument("--json", action="store_true", help="Emit safe diagnostic JSON")
    args = parser.parse_args(argv)
    try:
        result = check(args.database)
    except (ValueError, sqlite3.DatabaseError, OSError):
        # Do not disclose a sensitive local path, a host identity or DB content.
        print("Metrics diagnostic failed (invalid/unavailable database)", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
