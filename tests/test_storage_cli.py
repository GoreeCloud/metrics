"""Exercise consistent backup, readback and refusal to destroy files."""
from pathlib import Path
import os
import sqlite3
import stat
import time

import pytest
from server import storage_cli


def prepared_database(tmp_path: Path) -> Path:
    path = tmp_path / "live.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE systems (node_id TEXT PRIMARY KEY, hostname TEXT);
            CREATE TABLE samples (id INTEGER PRIMARY KEY, node_id TEXT, ts INTEGER);
        """)
        connection.execute("INSERT INTO systems VALUES (?, ?)", ("node-a", "Host A"))
        connection.execute("INSERT INTO samples (node_id, ts) VALUES (?, ?)",
                           ("node-a", int(time.time()) - 45 * 86400))
        connection.execute("INSERT INTO samples (node_id, ts) VALUES (?, ?)",
                           ("node-a", int(time.time())))
    return path


def test_backup_verify_and_rehearsal(tmp_path):
    live = prepared_database(tmp_path)
    backup = tmp_path / "backup.sqlite3"
    metadata = storage_cli.guarded_copy(str(live), str(backup))
    assert metadata["samples"] == 2
    assert len(metadata["sha256"]) == 64
    assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert storage_cli.inspect(str(backup))["systems"] == 1
    restored = tmp_path / "rehearsal.sqlite3"
    assert storage_cli.guarded_copy(str(backup), str(restored))["samples"] == 2
    with pytest.raises(ValueError, match="Refusing"):
        storage_cli.guarded_copy(str(live), str(restored))
    assert storage_cli.inspect(str(live))["samples"] == 2


def test_retention_preview_and_apply(tmp_path):
    live = prepared_database(tmp_path)
    assert storage_cli.retention(str(live), 30) == 1
    assert storage_cli.inspect(str(live))["samples"] == 2
    assert storage_cli.retention(str(live), 30, apply=True) == 1
    assert storage_cli.inspect(str(live))["samples"] == 1
    with pytest.raises(ValueError):
        storage_cli.retention(str(live), 0)


def test_rejects_nonmetrics_and_symlinks(tmp_path):
    bad = tmp_path / "bad.db"
    with sqlite3.connect(bad) as connection:
        connection.execute("CREATE TABLE unrelated(a)")
    with pytest.raises(ValueError):
        storage_cli.inspect(str(bad))
    link = tmp_path / "link.db"
    link.symlink_to(bad)
    with pytest.raises(ValueError):
        storage_cli.inspect(str(link))
    assert storage_cli.main(["--database", str(bad), "verify"]) == 2
