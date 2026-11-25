"""Hub SQLite files are private from first creation, including open umask."""
from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path

import pytest

from server.app import db, init_db


def test_new_hub_file_is_owner_only_with_permissive_process_umask(
        monkeypatch, tmp_path):
    path = tmp_path / "private" / "hub.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    prior = os.umask(0)
    try:
        init_db()
    finally:
        os.umask(prior)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.parent.is_dir()
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_existing_file_is_not_chmodded_or_replaced(monkeypatch, tmp_path):
    path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE unrelated_private(value TEXT)")
        conn.execute("INSERT INTO unrelated_private VALUES ('synthetic')")
    path.chmod(0o644)
    before = path.stat().st_ino
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    with pytest.raises(RuntimeError, match="Unrecognized existing database"):
        init_db()
    assert path.stat().st_ino == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT value FROM unrelated_private").fetchone() == ("synthetic",)


def test_existing_metrics_store_is_not_recreated(monkeypatch, tmp_path):
    path = tmp_path / "ready.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    init_db()
    before_inode = path.stat().st_ino
    with db() as conn:
        conn.execute("INSERT INTO systems VALUES (?,?,?,?)",
                     ("synthetic-host", "Synthetic", 1, 2))
    init_db()
    assert path.stat().st_ino == before_inode
    with db() as conn:
        assert conn.execute("SELECT hostname FROM systems").fetchone()[0] == "Synthetic"
