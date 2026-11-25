"""Operator-only SQLite backup, integrity checks, safe rehearsal restore and retention.

No daemon, network access, or production file replacement. No secrets in output.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from urllib.parse import quote
from pathlib import Path

TABLES = frozenset({"systems", "samples"})


def existing_database(filename: str) -> Path:
    path = Path(filename).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Database must be an existing regular file, not a symlink")
    return path.resolve()


def inspect(filename: str) -> dict[str, object]:
    path = existing_database(filename)
    with sqlite3.connect(f"file:{quote(path.as_posix(), safe="/")}?mode=ro", uri=True) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result != ("ok",):
            raise ValueError("Database failed SQLite integrity check")
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if not TABLES.issubset(tables):
            raise ValueError("Not a GoreeCloud Metrics database")
        return {
            "bytes": path.stat().st_size,
            "systems": connection.execute("SELECT COUNT(*) FROM systems").fetchone()[0],
            "samples": connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0],
        }


def guarded_copy(source: str, target: str) -> dict[str, object]:
    source_path = existing_database(source)
    inspect(str(source_path))
    target_path = Path(target).expanduser()
    if target_path.is_symlink() or target_path.exists():
        raise ValueError("Refusing to replace existing destination")
    if not target_path.parent.is_dir():
        raise ValueError("Destination parent directory does not exist")
    created = False
    try:
        # Atomic reservation (O_EXCL) and owner-only file permission.
        descriptor = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(descriptor)
        created = True
        with sqlite3.connect(f"file:{quote(source_path.as_posix(), safe="/")}?mode=ro", uri=True) as src:
            with sqlite3.connect(target_path) as dst:
                src.backup(dst, pages=100, sleep=0.05)
        status = inspect(str(target_path))
        digest = hashlib.sha256()
        with target_path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
        status["sha256"] = digest.hexdigest()
        return status
    except Exception:
        if created:
            target_path.unlink(missing_ok=True)
        raise


def retention(filename: str, days: int, apply: bool = False, now: int | None = None) -> int:
    """Host and container history share one explicit retention preview/apply."""
    if not 1 <= days <= 365:
        raise ValueError("Retention period must be 1–365 days")
    path = existing_database(filename)
    inspect(str(path))
    cutoff = (int(time.time()) if now is None else now) - days * 86400
    uri = f"file:{quote(path.as_posix(), safe='/')}?mode={'rw' if apply else 'ro'}"
    with sqlite3.connect(uri, uri=True) as connection:
        if apply:
            connection.execute("BEGIN IMMEDIATE")
        tables = {r[0] for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        count = connection.execute(
            "SELECT COUNT(*) FROM samples WHERE ts < ?", (cutoff,)
        ).fetchone()[0]
        if "container_samples" in tables:
            count += connection.execute(
                "SELECT COUNT(*) FROM container_samples WHERE ts < ?", (cutoff,)
            ).fetchone()[0]
        if apply:
            if "container_samples" in tables:
                connection.execute("DELETE FROM container_samples WHERE ts < ?", (cutoff,))
            connection.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
        return count


def forget_node(filename: str, node_id: str, apply: bool = False) -> dict[str, object]:
    """Operator-only preview and atomic erasure of an explicitly selected node."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", node_id):
        raise ValueError("Invalid node identifier")
    path = existing_database(filename)
    inspect(str(path))
    uri = f"file:{quote(path.as_posix(), safe='/')}?mode={'rw' if apply else 'ro'}"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if apply:
            connection.execute("BEGIN IMMEDIATE")
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        count = connection.execute(
            "SELECT COUNT(*) FROM systems WHERE node_id=?", (node_id,)
        ).fetchone()[0]
        if count != 1:
            raise ValueError("Node not registered in database")
        to_count = {
            "samples": "samples",
            "container_samples": "container_samples",
            "alert_state": "alert_state",
            "alert_events": "alert_events",
        }
        counts = {
            name: connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE node_id=?", (node_id,)
            ).fetchone()[0] if table in tables else 0
            for name, table in to_count.items()
        }
        if apply:
            # Clear dependent rows explicitly, including older databases
            # without foreign keys and separate alert-state tables.
            for name, table in to_count.items():
                if table in tables:
                    connection.execute(f"DELETE FROM {table} WHERE node_id=?", (node_id,))
            connection.execute("DELETE FROM systems WHERE node_id=?", (node_id,))
            if connection.execute(
                "SELECT COUNT(*) FROM systems WHERE node_id=?", (node_id,)
            ).fetchone()[0]:
                raise sqlite3.DatabaseError("Node erasure did not complete")
        return {"node_id": node_id, "matching_systems": count,
                **{f"matching_{name}": value for name, value in counts.items()},
                "applied": apply}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GoreeCloud Metrics safe database operations")
    parser.add_argument("--database", default=os.environ.get("METRICS_DB_PATH", "./data/metrics.sqlite3"))
    commands = parser.add_subparsers(dest="operation", required=True)
    commands.add_parser("verify", help="Run read-only integrity and table checks")
    copy = commands.add_parser("backup", help="Make a consistent live SQLite snapshot to a NEW file")
    copy.add_argument("destination")
    restore = commands.add_parser("restore-rehearsal", help="Restore backup to a NEW path; never overwrite")
    restore.add_argument("backup_file")
    restore.add_argument("destination")
    prune = commands.add_parser("retention", help="Preview retention purge, or explicitly apply it")
    prune.add_argument("--days", type=int, default=30)
    prune.add_argument("--apply", action="store_true")
    forget = commands.add_parser("forget-node",
                                 help="Preview one node's host, container and alert data erasure")
    forget.add_argument("--node-id", required=True)
    forget.add_argument("--apply", action="store_true",
                        help="Irreversibly erase this registered node and associated data")
    args = parser.parse_args(argv)
    try:
        if args.operation == "verify":
            status = inspect(args.database)
        elif args.operation == "backup":
            status = guarded_copy(args.database, args.destination)
        elif args.operation == "restore-rehearsal":
            status = guarded_copy(args.backup_file, args.destination)
        elif args.operation == "retention":
            amount = retention(args.database, args.days, args.apply)
            status = {"matching_samples": amount, "applied": args.apply, "retention_days": args.days}
        elif args.operation == "forget-node":
            status = forget_node(args.database, args.node_id, args.apply)
        else:
            raise ValueError("Unknown storage operation")
        for key, value in status.items():
            print(f"{key}: {value}")
        return 0
    except (ValueError, OSError, sqlite3.DatabaseError) as error:
        print(f"Storage operation failed: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
