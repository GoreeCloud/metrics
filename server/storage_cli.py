"""Operator-only SQLite backup, integrity checks, safe rehearsal restore and retention.

No daemon, network access, or production file replacement. No secrets in output.
"""
from __future__ import annotations

import argparse
import hashlib
import os
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
    if not 1 <= days <= 365:
        raise ValueError("Retention period must be 1–365 days")
    path = existing_database(filename)
    inspect(str(path))
    cutoff = int(time.time()) if now is None else now
    cutoff -= days * 86400
    with sqlite3.connect(path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM samples WHERE ts < ?", (cutoff,)).fetchone()[0]
        if apply:
            connection.execute("DELETE FROM samples WHERE ts < ?", (cutoff,))
        return count


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
    args = parser.parse_args(argv)
    try:
        if args.operation == "verify":
            status = inspect(args.database)
        elif args.operation == "backup":
            status = guarded_copy(args.database, args.destination)
        elif args.operation == "restore-rehearsal":
            status = guarded_copy(args.backup_file, args.destination)
        else:
            amount = retention(args.database, args.days, args.apply)
            status = {"matching_samples": amount, "applied": args.apply, "retention_days": args.days}
        for key, value in status.items():
            print(f"{key}: {value}")
        return 0
    except (ValueError, OSError, sqlite3.DatabaseError) as error:
        print(f"Storage operation failed: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
