"""Additive host-id index supports bounded latest-sample queries at large scale."""
from __future__ import annotations

import sqlite3

from server import app as metrics
from server import doctor


def test_latest_sample_index_is_adopted_without_touching_legacy_rows(
        monkeypatch, tmp_path):
    path = tmp_path / "host-index.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    metrics.init_db()
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO systems VALUES(?,?,?,?)",
            [("host-a", "A", 1, 1), ("host-b", "B", 1, 1)])
        connection.executemany(
            """INSERT INTO samples(node_id,ts,cpu,memory,disk,memory_bytes,
            disk_bytes,rx_bytes,tx_bytes,uptime_seconds)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [("host-a" if i % 11 == 0 else "host-b",
              100 + i, 1, 1, 1, 100, 200, i, i, i)
             for i in range(12000)])
        before = connection.execute(
            "SELECT COUNT(*), MIN(id), MAX(id) FROM samples"
        ).fetchone()
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT ts,rx_bytes,tx_bytes FROM samples "
            "WHERE node_id=? ORDER BY id DESC LIMIT 2", ("host-a",)
        ).fetchall()
        assert any("samples_node_id_desc" in str(row) for row in plan), plan
        last = connection.execute(
            "SELECT id FROM samples WHERE node_id=? ORDER BY id DESC LIMIT 2",
            ("host-a",)
        ).fetchall()
        assert len(last) == 2 and last[0][0] > last[1][0]

    assert doctor.check(str(path))["history_indexes_present"] is True
    metrics.init_db()
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM samples"
                                  ).fetchone() == before


def test_doctor_calls_out_missing_id_index_without_mutating_database(
        monkeypatch, tmp_path):
    path = tmp_path / "missing-index.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    metrics.init_db()
    with sqlite3.connect(path) as conn:
        conn.execute("DROP INDEX samples_node_id_desc")
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='samples_node_id_desc'"
        ).fetchone()[0] == 0
    status = doctor.check(str(path))
    assert status["status"] == "review_required"
    assert status["history_indexes_present"] is False
    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='samples_node_id_desc'"
        ).fetchone()[0] == 0
    metrics.init_db()
    assert doctor.check(str(path))["status"] == "ready"
