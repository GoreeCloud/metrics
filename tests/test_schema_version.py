"""SQLite schema version adoption: no data loss, fail closed for unknown revisions."""
from __future__ import annotations

import sqlite3

import pytest

from server import app as metrics


def test_new_database_gets_explicit_version(monkeypatch, tmp_path):
    file = tmp_path / "new.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(file))
    metrics.init_db()
    with sqlite3.connect(file) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == metrics.SCHEMA_VERSION
        assert db.execute("SELECT count(*) FROM systems").fetchone()[0] == 0
    metrics.init_db()


def test_existing_unversioned_host_rows_are_preserved(monkeypatch, tmp_path):
    file = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(file) as db:
        db.executescript("""
          CREATE TABLE systems (node_id TEXT PRIMARY KEY,hostname TEXT NOT NULL,
              first_seen INTEGER NOT NULL,last_seen INTEGER NOT NULL);
          CREATE TABLE samples (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              node_id TEXT NOT NULL REFERENCES systems(node_id) ON DELETE CASCADE,
              ts INTEGER NOT NULL,cpu REAL NOT NULL,memory REAL NOT NULL,disk REAL NOT NULL,
              memory_bytes INTEGER NOT NULL,disk_bytes INTEGER NOT NULL,
              rx_bytes INTEGER NOT NULL,tx_bytes INTEGER NOT NULL,
              uptime_seconds REAL NOT NULL);
        """)
        db.execute("INSERT INTO systems VALUES ('legacy', 'Synthetic legacy', 100, 100)")
        db.execute("INSERT INTO samples (node_id,ts,cpu,memory,disk,memory_bytes,"
                   "disk_bytes,rx_bytes,tx_bytes,uptime_seconds) VALUES "
                   "('legacy',100,1,2,3,4,5,6,7,8)")
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
    monkeypatch.setenv("METRICS_DB_PATH", str(file))
    metrics.init_db()
    with sqlite3.connect(file) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("SELECT hostname FROM systems WHERE node_id='legacy'").fetchone()[0] == "Synthetic legacy"
        assert db.execute("SELECT count(*) FROM samples").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM container_samples").fetchone()[0] == 0


def test_future_schema_is_rejected_without_modifying_database(monkeypatch, tmp_path):
    file = tmp_path / "future.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(file))
    metrics.init_db()
    with sqlite3.connect(file) as db:
        db.execute("PRAGMA user_version=99")
        db.execute("INSERT INTO systems VALUES ('future','Preserve',1,2)")
    with pytest.raises(RuntimeError, match="newer or unsupported"):
        metrics.init_db()
    with sqlite3.connect(file) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99
        assert db.execute("SELECT hostname FROM systems").fetchone()[0] == "Preserve"


def test_partial_or_unsupported_legacy_schema_fails_closed(monkeypatch, tmp_path):
    file = tmp_path / "partial.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(file))
    with sqlite3.connect(file) as db:
        db.execute("CREATE TABLE systems(node_id TEXT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="Incomplete"):
        metrics.init_db()
    with sqlite3.connect(file) as db:
        assert "samples" not in {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
