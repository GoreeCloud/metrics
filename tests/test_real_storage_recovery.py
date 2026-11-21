"""Real hub schema -> consistent live snapshot -> isolated readback rehearsal."""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.storage_cli import guarded_copy, inspect


def test_live_metrics_backup_and_restore_rehearsal(monkeypatch, tmp_path):
    db_path = tmp_path / "metrics.sqlite3"
    backup_path = tmp_path / "metrics.snapshot.sqlite3"
    restored_path = tmp_path / "metrics.restored.sqlite3"
    monkeypatch.setenv("METRICS_DB_PATH", str(db_path))
    monkeypatch.setenv("METRICS_ADMIN_TOKEN", "a" * 40)
    monkeypatch.setenv("METRICS_AGENT_TOKENS", json.dumps({"node-test": "b" * 40}))
    monkeypatch.delenv("METRICS_STATUS_TOKEN", raising=False)
    payload = {
        "node_id": "node-test",
        "hostname": "Synthetic host only",
        "cpu_percent": 24,
        "memory_percent": 33,
        "disk_percent": 19,
        "memory_used_bytes": 1024,
        "disk_used_bytes": 2048,
        "rx_bytes": 100,
        "tx_bytes": 150,
        "uptime_seconds": 100,
        "containers": [
            {"name": "synthetic-container", "cpu_percent": 4, "memory_percent": 5,
             "rx_bytes": 20, "tx_bytes": 30}
        ],
    }
    with TestClient(app) as client:
        assert client.post("/api/v1/ingest", json=payload,
                           headers={"X-Agent-Token": "b" * 40}).status_code == 202
        snapshot = guarded_copy(str(db_path), str(backup_path))
        assert snapshot["systems"] == 1 and snapshot["samples"] == 1
        assert len(snapshot["sha256"]) == 64
        with pytest.raises(ValueError, match="Refusing"):
            guarded_copy(str(backup_path), str(db_path))
    restored = guarded_copy(str(backup_path), str(restored_path))
    assert restored["systems"] == snapshot["systems"]
    assert restored["samples"] == snapshot["samples"]
    with sqlite3.connect(restored_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute(
            "SELECT hostname FROM systems WHERE node_id='node-test'"
        ).fetchone()[0] == "Synthetic host only"
        assert connection.execute(
            "SELECT name FROM container_samples WHERE node_id='node-test'"
        ).fetchone()[0] == "synthetic-container"
        assert connection.execute(
            "SELECT COUNT(*) FROM samples"
        ).fetchone()[0] == 1
    assert inspect(str(db_path))["samples"] == 1
