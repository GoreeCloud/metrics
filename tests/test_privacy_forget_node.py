"""Privacy erasure and complete retention on synthetic isolated databases only."""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from server import app as metrics
from server import notifications, storage_cli


def sample(node):
    return {"node_id": node, "hostname": "Synthetic host " + node,
            "cpu_percent": 2, "memory_percent": 3, "disk_percent": 4,
            "memory_used_bytes": 55, "disk_used_bytes": 88,
            "rx_bytes": 1, "tx_bytes": 2, "uptime_seconds": 20,
            "containers": [{"name": "synthetic-container",
                            "cpu_percent": 5, "memory_percent": 6,
                            "rx_bytes": 1, "tx_bytes": 2}]}


def fixture(monkeypatch, tmp_path):
    path = tmp_path / "synthetic.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(path))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps(
        {"node-a": "b" * 40, "node-b": "c" * 40}))
    with TestClient(metrics.app) as client:
        for node, token in (("node-a", "b" * 40), ("node-b", "c" * 40)):
            response = client.post("/api/v1/ingest", json=sample(node),
                                   headers={"X-Agent-Token": token})
            assert response.status_code == 202, response.text
    notifications.initialize_journal()
    notifications.record_transitions(
        [{"node_id": "node-a", "metric": "cpu", "message": "Synthetic A"},
         {"node_id": "node-b", "metric": "disk", "message": "Synthetic B"}],
        now=2_000_000_000)
    return path


def test_forget_is_preview_first_and_isolates_other_nodes(monkeypatch, tmp_path):
    path = fixture(monkeypatch, tmp_path)
    dry = storage_cli.forget_node(str(path), "node-a")
    assert not dry["applied"]
    assert all(dry[key] == 1 for key in (
        "matching_systems", "matching_samples", "matching_container_samples",
        "matching_alert_state", "matching_alert_events"))
    assert storage_cli.main(
        ["--database", str(path), "forget-node", "--node-id", "node-a"]) == 0
    assert storage_cli.inspect(str(path))["systems"] == 2
    changed = storage_cli.forget_node(str(path), "node-a", apply=True)
    assert changed["applied"]
    with sqlite3.connect(path) as db:
        for table in ("systems", "samples", "container_samples",
                      "alert_state", "alert_events"):
            assert db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE node_id='node-a'"
            ).fetchone()[0] == 0
            assert db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE node_id='node-b'"
            ).fetchone()[0] == 1
    with pytest.raises(ValueError, match="not registered"):
        storage_cli.forget_node(str(path), "node-a", apply=True)
    assert storage_cli.main(
        ["--database", str(path), "forget-node",
         "--node-id", "nonexistent", "--apply"]) == 2


def test_forget_validation_rejects_invalid_identity(monkeypatch, tmp_path):
    path = fixture(monkeypatch, tmp_path)
    for node in ("../node-a", "NODE-A", "node-a/../../", "n" * 64):
        with pytest.raises(ValueError, match="Invalid"):
            storage_cli.forget_node(str(path), node, apply=True)
    assert storage_cli.inspect(str(path))["systems"] == 2


def test_retention_covers_container_samples_too(monkeypatch, tmp_path):
    path = fixture(monkeypatch, tmp_path)
    now = 2_000_000_000
    with sqlite3.connect(path) as db:
        db.execute("UPDATE samples SET ts=? WHERE node_id='node-a'", (now - 40*86400,))
        db.execute("UPDATE container_samples SET ts=? WHERE node_id='node-a'", (now - 40*86400,))
        db.execute("UPDATE samples SET ts=? WHERE node_id='node-b'", (now,))
        db.execute("UPDATE container_samples SET ts=? WHERE node_id='node-b'", (now,))
    assert storage_cli.retention(str(path), 30, now=now) == 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM container_samples").fetchone()[0] == 2
    assert storage_cli.retention(str(path), 30, apply=True, now=now) == 2
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM container_samples").fetchone()[0] == 1
