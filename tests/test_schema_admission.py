"""Refuse unknown/partial storage identity before any schema or WAL mutation."""
from __future__ import annotations

import sqlite3

import pytest
from server import app as metrics


def sqlite_state(path):
    with sqlite3.connect(path) as conn:
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        return journal, version, tables


def test_unrelated_database_not_adopted_or_switched_to_wal(monkeypatch, tmp_path):
    path = tmp_path / "other-application.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE unrelated_private_records(secret TEXT)")
        conn.execute("INSERT INTO unrelated_private_records VALUES ('synthetic')")
    before = sqlite_state(path)
    assert before[0] == "delete"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    with pytest.raises(RuntimeError, match="Unrecognized"):
        metrics.init_db()
    assert sqlite_state(path) == before
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT secret FROM unrelated_private_records"
        ).fetchone() == ("synthetic",)


def test_orphan_container_table_is_rejected_without_rebuilding(monkeypatch, tmp_path):
    path = tmp_path / "orphan.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE container_samples(id INTEGER, name TEXT)")
    before = sqlite_state(path)
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    with pytest.raises(RuntimeError, match="Incomplete Metrics container schema"):
        metrics.init_db()
    assert sqlite_state(path) == before


def test_versioned_missing_container_table_requires_manual_recovery(
        monkeypatch, tmp_path):
    path = tmp_path / "versioned-damage.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    metrics.init_db()
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE container_samples")
        before = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert "systems" in before and "samples" in before
    with pytest.raises(RuntimeError, match="Incomplete versioned Metrics"):
        metrics.init_db()
    with sqlite3.connect(path) as conn:
        after = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert after == before


def test_unknown_future_version_preserves_original_journal_mode(monkeypatch, tmp_path):
    path = tmp_path / "future.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version=400")
        conn.execute("CREATE TABLE another_app(id INTEGER PRIMARY KEY)")
    assert sqlite_state(path)[0] == "delete"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    with pytest.raises(RuntimeError, match="newer or unsupported"):
        metrics.init_db()
    assert sqlite_state(path)[0] == "delete"
    assert sqlite_state(path)[1] == 400


def test_symlink_database_path_is_not_followed(monkeypatch, tmp_path):
    target = tmp_path / "private-target.sqlite3"
    with sqlite3.connect(target) as conn:
        conn.execute("CREATE TABLE untrusted(data TEXT)")
        conn.execute("INSERT INTO untrusted VALUES ('synthetic')")
    before = sqlite_state(target)
    link = tmp_path / "pointing-at-unrelated.sqlite3"
    link.symlink_to(target)
    monkeypatch.setenv("METRICS_DB_PATH", str(link))
    with pytest.raises(OSError, match="symlink"):
        metrics.init_db()
    assert sqlite_state(target) == before
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT data FROM untrusted").fetchone() == ("synthetic",)

